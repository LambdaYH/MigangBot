import traceback
from typing import Any, Dict, List

from nonebot.log import logger
from nonebot.matcher import Matcher
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import AIMessage, HumanMessage
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from migang.core.models import ChatGPTChatHistory
from migang.core.utils.langchain_tool import search_plugin_tool

from .prompt import build_chat_prompt
from .settings import ChatAgentSettings
from .image_intent import (
    is_explicit_image_tool_query,
    is_general_image_understanding_query,
)
from .utils import (
    get_bot_name,
    get_user_name,
    uniform_message,
    strip_think_tags,
    deserialize_message,
    message_content_to_text,
    has_direct_output_marker,
    message_to_model_content,
    is_langchain_message_payload,
    serialize_langchain_messages,
    deserialize_langchain_messages,
)


class LangChainChatBot:
    def __init__(self):
        self.settings = ChatAgentSettings.load()
        self.api_keys = self.settings.api_keys
        self.api_base = self.settings.api_base
        self.model = self.settings.model
        self.temperature = self.settings.temperature
        self.max_tokens = self.settings.reply_max_tokens
        self.top_p = self.settings.top_p
        self.frequency_penalty = self.settings.frequency_penalty
        self.presence_penalty = self.settings.presence_penalty
        self.timeout = self.settings.timeout
        self.memory_short_length = self.settings.memory_short_length
        self.memory_max_length = self.settings.memory_max_length
        self.personality = self.settings.personality
        self.max_response_per_msg = self.settings.max_response_per_msg

        self.current_key_index = 0
        self.llm = self._create_llm()
        self.tools = self._create_tools()

    def _create_llm(self) -> ChatOpenAI:
        """创建langchain的ChatOpenAI实例，支持异步流式输出"""
        api_key = self.api_keys[self.current_key_index] if self.api_keys else ""

        kwargs = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "request_timeout": self.timeout,
            "api_key": api_key,
            "streaming": True,  # 启用流式输出
            "extra_body": {
                "reasoning_split": self.settings.reasoning_split,
            },
        }

        if self.api_base:
            kwargs["base_url"] = self.api_base

        return ChatOpenAI(**kwargs)

    def _switch_api_key(self):
        """切换到下一个API密钥"""
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            self.llm = self._create_llm()
            logger.info(f"已切换到API密钥索引: {self.current_key_index}")

    def _create_tools(self) -> List:
        """创建工具列表"""
        from .langchain_tools import tool_manager

        return tool_manager.get_tools()

    async def _get_chat_history(self, thread_id: str, bot: Bot) -> List:
        """根据 thread_id 获取历史消息，返回 langchain 消息格式"""
        messages = []
        # 解析 thread_id
        if thread_id.startswith("group-"):
            group_id = int(thread_id.split("-")[1])
            chat_histories = (
                await ChatGPTChatHistory.filter(group_id=group_id)
                .order_by("-time")
                .limit(self.memory_short_length)
            )
        elif thread_id.startswith("private-"):
            user_id = int(thread_id.split("-")[1])
            chat_histories = (
                await ChatGPTChatHistory.filter(user_id=user_id, group_id=0)
                .order_by("-time")
                .limit(self.memory_short_length)
            )
        else:
            chat_histories = []

        for chat in reversed(chat_histories):
            if chat.target_id:  # 机器人回复
                if getattr(chat, "is_bot", False):
                    if is_langchain_message_payload(chat.message):
                        messages.extend(deserialize_langchain_messages(chat.message))
                    else:
                        message_content = await message_to_model_content(
                            deserialize_message(chat.message),
                            group_id=chat.group_id,
                            bot=bot,
                            prefix_text="",
                        )
                        messages.append(AIMessage(content=message_content))
                else:
                    user_name = await get_user_name(
                        bot=bot, group_id=chat.group_id, user_id=chat.user_id
                    )
                    message_content = await message_to_model_content(
                        deserialize_message(chat.message),
                        group_id=chat.group_id,
                        bot=bot,
                        prefix_text=f"{user_name}: ",
                    )
                    messages.append(HumanMessage(content=message_content))
            else:
                user_name = await get_user_name(
                    bot=bot, group_id=chat.group_id, user_id=chat.user_id
                )
                message_content = await message_to_model_content(
                    deserialize_message(chat.message), group_id=chat.group_id, bot=bot
                )
                if isinstance(message_content, str):
                    message_content = f"{user_name}: {message_content}"
                else:
                    message_content = [
                        {"type": "text", "text": f"{user_name}: "},
                        *message_content,
                    ]
                messages.append(HumanMessage(content=message_content))
        return messages

    async def chat(
        self,
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot,
        trigger_text: List[Dict[str, Any]],
    ) -> None:
        """主要的聊天处理函数"""
        max_retries = len(self.api_keys) if self.api_keys else 1

        # 生成 thread_id
        if hasattr(event, "group_id"):
            thread_id = f"group-{event.group_id}"
        else:
            thread_id = f"private-{event.user_id}"

        for attempt in range(max_retries):
            try:
                bot_name = get_bot_name(bot=bot)

                # 获取聊天历史
                chat_history = await self._get_chat_history(thread_id, bot)

                uniformed_message = await uniform_message(
                    deserialize_message(trigger_text), group_id=event.group_id, bot=bot
                )
                has_image = any(item.get("type") == "image" for item in trigger_text)
                direct_image_chat_mode = (
                    has_image
                    and is_general_image_understanding_query(uniformed_message)
                    and not is_explicit_image_tool_query(uniformed_message)
                )

                # 获取相关插件
                relative_plugin = await search_plugin_tool(
                    uniformed_message,
                    has_image=has_image,
                )

                # 创建提示模板
                prompt = build_chat_prompt(
                    bot_name=bot_name,
                    personality=self.personality,
                    relative_plugin=relative_plugin,
                )

                user_name = await get_user_name(
                    bot=bot, group_id=event.group_id, user_id=event.user_id
                )
                input_message = await message_to_model_content(
                    deserialize_message(trigger_text),
                    group_id=event.group_id,
                    bot=bot,
                    prefix_text=f"{user_name}: ",
                )
                if isinstance(input_message, list):
                    image_block_count = sum(
                        1 for item in input_message if item.get("type") == "image_url"
                    )
                    logger.info(
                        f"发送多模态消息给模型: text_blocks={sum(1 for item in input_message if item.get('type') == 'text')} | image_blocks={image_block_count}"
                    )
                else:
                    logger.info("发送纯文本消息给模型")
                # 组装 messages
                messages = chat_history + [HumanMessage(content=input_message)]

                import re

                from nonebot.adapters.onebot.v11 import Message

                if direct_image_chat_mode:
                    logger.info("图片理解模式：保留工具，由模型自行决策")

                agent = create_react_agent(self.llm, tools=self.tools, prompt=prompt)
                input_message_count = len(messages)
                latest_state = None

                async for stream_item in agent.astream(
                    {"messages": messages},
                    stream_mode=["messages", "values"],
                ):
                    if (
                        isinstance(stream_item, tuple)
                        and len(stream_item) == 2
                        and stream_item[0] == "values"
                    ):
                        latest_state = stream_item[1]

                if not latest_state or "messages" not in latest_state:
                    raise RuntimeError("未获取到完整的 agent 消息状态")

                final_messages = latest_state["messages"]
                new_messages = final_messages[input_message_count:]
                assistant_messages = [
                    message
                    for message in new_messages
                    if isinstance(message, AIMessage)
                ]
                final_response_text = ""
                if has_direct_output_marker(new_messages):
                    logger.info("检测到工具结果已直接发送给用户，跳过补充回复")
                else:
                    final_ai_message = (
                        assistant_messages[-1] if assistant_messages else None
                    )
                    if final_ai_message is not None:
                        final_response_text = strip_think_tags(
                            message_content_to_text(final_ai_message.content)
                        )

                sent_parts = []
                if final_response_text:
                    for part in final_response_text.split("*;"):
                        if len(sent_parts) >= self.max_response_per_msg:
                            break
                        part = part.strip()
                        if part and not re.match(r"^[^\u4e00-\u9fa5\w]{1}$", part):
                            await matcher.send(Message(part))
                            sent_parts.append(part)
                if len(final_response_text.split("*;")) > self.max_response_per_msg:
                    logger.error("大模型回复内容过多，已截断")
                    await matcher.send("由于内容过多，麦克风被抢走了...")
                elif not final_response_text and has_image:
                    logger.warning("当前消息包含图片，但模型未返回可见内容")
                    await matcher.send("我收到图片了，但这次没有成功看出来。你可以再具体问我想看图里的哪部分。")
                full_response_str = (
                    "*;".join(sent_parts) if sent_parts else final_response_text
                )

                # 记录用户发言
                await ChatGPTChatHistory(
                    user_id=event.user_id,
                    group_id=getattr(event, "group_id", 0),
                    target_id=event.self_id,
                    message=trigger_text,
                    is_bot=False,
                ).save()
                # 记录回复
                await ChatGPTChatHistory(
                    user_id=event.self_id,
                    group_id=getattr(event, "group_id", 0),
                    target_id=event.user_id,
                    message=serialize_langchain_messages(new_messages),
                    is_bot=True,  # 机器人消息
                ).save()

                # 成功完成，退出重试循环
                return

            except Exception as e:
                error_msg = str(e)
                logger.error(
                    f"聊天处理过程中发生错误 (尝试 {attempt + 1}/{max_retries}): {error_msg}"
                )
                logger.debug(f"错误详情: {traceback.format_exc()}")

                # 检查是否是API密钥相关错误
                if "rate limit" in error_msg.lower() or "api key" in error_msg.lower():
                    if attempt < max_retries - 1:  # 不是最后一次尝试
                        self._switch_api_key()
                        logger.info(f"由于API错误，切换密钥后重试...")
                        continue

                # 如果是最后一次尝试或其他错误，直接返回错误消息
                if attempt == max_retries - 1:
                    await matcher.finish(f"抱歉，我遇到了一些问题: {error_msg}")
                else:
                    continue


# 全局实例
langchain_chatbot = LangChainChatBot()
