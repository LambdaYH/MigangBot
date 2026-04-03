from typing import Tuple
from datetime import datetime

from nonebot.log import logger
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from migang.core.models import ChatGPTChatHistory

from .config import sync_get_agent_config
from .intent_judge import chat_intent_judge
from .dialog_window import dialog_window_manager
from .utils import get_bot_name, gen_chat_text, is_reply_to_bot, serialize_message

ignore_prefix: Tuple[str] = tuple(
    sync_get_agent_config("ignore_prefix", default_value=[]) or []
)
dialog_window_minutes: int = int(
    sync_get_agent_config("dialog_window_minutes", default_value=10) or 10
)


async def pre_check(event: GroupMessageEvent, bot: Bot, state: T_State) -> bool:
    plain_text = event.get_plaintext()
    has_image = any(seg.type == "image" for seg in event.message)
    window_was_active = dialog_window_manager.is_active(event)
    window_state = dialog_window_manager.get_state(event) if window_was_active else None
    if not plain_text and not has_image:
        logger.debug("空消息，不处理")
        return False
    if plain_text and plain_text.startswith(ignore_prefix):
        logger.debug("忽略消息前缀")
        return False
    chat_text, is_tome = await gen_chat_text(
        event=event,
        bot=bot,
        include_reply_context=False,
    )
    judge_text, _ = await gen_chat_text(
        event=event,
        bot=bot,
        include_reply_context=True,
    )
    is_tome = is_tome or event.is_tome()
    bot_name = get_bot_name(bot=bot)
    reply_to_bot = is_reply_to_bot(event=event, bot=bot)

    # 是否需要响应
    explicit_triggered = (
        is_tome or reply_to_bot or (bot_name.lower() in chat_text.lower())
    )
    triggered = explicit_triggered
    trigger_reason = "reply_to_bot" if reply_to_bot else "explicit"

    if not triggered and dialog_window_manager.is_active(event):
        try:
            judge_result = await chat_intent_judge.should_reply(
                event=event,
                bot=bot,
                message_text=judge_text,
                has_image=has_image,
                window_source=window_state.source if window_state else "chat",
            )
        except Exception as e:
            logger.warning(f"连续对话意图识别失败，跳过本次续聊判断: {e}")
        else:
            if judge_result.end_session:
                dialog_window_manager.clear(event)
                logger.info(f"检测到终止会话意图，已关闭连续对话窗口 | group={event.group_id}")
            triggered = judge_result.should_reply
            trigger_reason = f"window:{judge_result.reason}"

    # 记录消息，虽然可能与我无关，但是记录保证对上下文的理解
    record_msg = await serialize_message(event.message, bot=bot, event=event)
    if is_tome:
        record_msg = [
            {"type": "at", "data": {"qq": bot.self_id}},
            {"type": "text", "data": {"text": " "}},
        ] + record_msg

    if triggered:
        logger.info(f"符合发言条件，开始回复 | reason={trigger_reason}")
        state["gpt_trigger_text"] = record_msg
        state["refresh_dialog_window"] = True
        state["window_was_active"] = window_was_active
    else:
        await ChatGPTChatHistory(
            user_id=event.user_id,
            group_id=event.group_id,
            target_id=event.self_id if triggered else None,
            message=record_msg,
            is_bot=False,  # 用户消息
        ).save()
    return triggered


async def do_chat(
    matcher: Matcher, event: GroupMessageEvent, bot: Bot, state: T_State
) -> None:
    trigger_text = state["gpt_trigger_text"]

    start_time = datetime.now()

    # 使用新的langchain实现
    from .langchain_chat import langchain_chatbot

    await langchain_chatbot.chat(matcher, event, bot, trigger_text)
    if state.get("refresh_dialog_window"):
        dialog_window_manager.refresh(event, dialog_window_minutes, source="chat")
        if state.get("window_was_active"):
            logger.info(
                f"已刷新连续对话窗口 | group={event.group_id} | duration={dialog_window_minutes}min"
            )
        else:
            logger.info(
                f"已进入连续对话窗口 | group={event.group_id} | duration={dialog_window_minutes}min"
            )

    logger.debug(f"对话响应完成 | 耗时: {(datetime.now() - start_time).seconds}s")
