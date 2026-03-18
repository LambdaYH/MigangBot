from __future__ import annotations

import re
import json
from dataclasses import dataclass

from nonebot.log import logger
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from migang.core.models import ChatGPTChatHistory

from .settings import ChatAgentSettings
from .utils import (
    get_user_name,
    uniform_message,
    deserialize_message,
    message_content_to_text,
    is_langchain_message_payload,
    deserialize_langchain_messages,
)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(slots=True)
class IntentJudgeResult:
    should_reply: bool
    reason: str


class ChatIntentJudge:
    def __init__(self) -> None:
        self._llm: ChatOpenAI | None = None
        self._llm_signature: tuple | None = None

    async def should_reply(
        self,
        event: GroupMessageEvent,
        bot: Bot,
        message_text: str,
        has_image: bool,
    ) -> IntentJudgeResult:
        settings = ChatAgentSettings.load()
        if not settings.intent_judge_enabled:
            return IntentJudgeResult(False, "intent_judge_disabled")

        llm = self._get_llm(settings)
        history_text = await self._build_history(
            event, bot, settings.intent_history_length
        )
        image_hint = "是" if has_image else "否"
        prompt = (
            "你是群聊机器人的会话路由器。当前已经存在一个 10 分钟的连续对话窗口。\n"
            "你的任务是判断：用户最新一句话是否仍然是在和机器人继续对话，是否需要机器人回复。\n"
            '返回 JSON，格式固定为 {"should_reply": true/false, "reason": "简短原因"}。\n'
            "判断规则：\n"
            "1. 如果是在承接机器人上一轮回答、追问、补充说明、纠正、要求继续处理，should_reply=true。\n"
            "2. 如果是在窗口内继续打招呼、寒暄、回应机器人，也应视为和机器人继续对话，should_reply=true。\n"
            "3. 如果明显是在和群友说话、普通群聊、和机器人上下文无关，should_reply=false。\n"
            "4. 如果消息里有图片，且像是在让机器人继续看图、解释刚发的图片，也算 should_reply=true。\n"
            "5. 输出只能是 JSON，不要附加解释。\n\n"
            f"该群最近会话历史：\n{history_text}\n\n"
            f"当前消息是否带图片：{image_hint}\n"
            f"当前消息内容：{message_text or '[空文本，仅图片或非文本内容]'}"
        )
        response = await llm.ainvoke(prompt)
        result = self._parse_response(response)
        message_preview = (message_text or "[空文本]").replace("\n", " ").strip()
        if len(message_preview) > 60:
            message_preview = message_preview[:57] + "..."
        logger.info(
            f"连续对话意图识别: should_reply={result.should_reply} | reason={result.reason} | message={message_preview}"
        )
        return result

    def _get_llm(self, settings: ChatAgentSettings) -> ChatOpenAI:
        api_keys = settings.intent_api_keys or settings.api_keys
        api_key = api_keys[0] if api_keys else ""
        model = settings.intent_model or settings.model
        base_url = settings.intent_api_base or settings.api_base
        timeout = settings.intent_timeout or settings.timeout
        signature = (
            model,
            base_url,
            api_key,
            timeout,
            settings.reasoning_split,
        )
        if self._llm is not None and self._llm_signature == signature:
            return self._llm

        kwargs = {
            "model": model,
            "temperature": 0,
            "max_tokens": 128,
            "request_timeout": timeout,
            "api_key": api_key,
            "streaming": False,
            "extra_body": {
                "reasoning_split": settings.reasoning_split,
            },
        }
        if base_url:
            kwargs["base_url"] = base_url

        self._llm = ChatOpenAI(**kwargs)
        self._llm_signature = signature
        return self._llm

    async def _build_history(
        self,
        event: GroupMessageEvent,
        bot: Bot,
        limit: int,
    ) -> str:
        rows = (
            await ChatGPTChatHistory.filter(group_id=event.group_id)
            .order_by("-time")
            .limit(limit)
        )
        if not rows:
            return "无"

        lines: list[str] = []
        for row in reversed(rows):
            if getattr(row, "is_bot", False):
                bot_text = self._extract_bot_text(row.message)
                if bot_text:
                    lines.append(f"机器人: {bot_text}")
                continue

            try:
                user_text = await uniform_message(
                    deserialize_message(row.message),
                    group_id=row.group_id,
                    bot=bot,
                )
                user_name = await get_user_name(
                    bot=bot, group_id=row.group_id, user_id=row.user_id
                )
            except Exception:
                user_text = "[消息解析失败]"
                user_name = "用户"
            if user_text:
                lines.append(f"{user_name}: {user_text}")

        return "\n".join(lines) if lines else "无"

    def _extract_bot_text(self, payload: object) -> str:
        if is_langchain_message_payload(payload):
            messages = deserialize_langchain_messages(payload)
            ai_text = [
                message_content_to_text(message.content).strip()
                for message in messages
                if isinstance(message, AIMessage)
            ]
            ai_text = [text for text in ai_text if text]
            return ai_text[-1] if ai_text else ""
        return str(payload or "")

    def _parse_response(self, response: object) -> IntentJudgeResult:
        text = message_content_to_text(getattr(response, "content", response)).strip()
        match = _JSON_BLOCK_RE.search(text)
        if match:
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                return IntentJudgeResult(
                    should_reply=bool(payload.get("should_reply")),
                    reason=str(payload.get("reason", "")).strip() or "json_result",
                )
        lowered = text.lower()
        should_reply = '"should_reply": true' in lowered or "true" == lowered
        reason = text[:80] if text else "parse_fallback"
        return IntentJudgeResult(should_reply=should_reply, reason=reason)


chat_intent_judge = ChatIntentJudge()
