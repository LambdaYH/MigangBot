import traceback
from datetime import datetime
from typing import Any, Dict, List

from nonebot.log import logger
from nonebot.matcher import Matcher
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import AIMessage, HumanMessage
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from migang.core import sync_get_config
from migang.core.utils.langchain_tool import search_plugin_tool
from migang.core.models import ChatGPTChatHistory, ChatGPTChatImpression

from .utils import (
    get_bot_name,
    gen_chat_line,
    get_user_name,
    uniform_message,
    serialize_message,
    deserialize_message,
)


class LangChainChatBot:
    def __init__(self):
        self.api_keys = sync_get_config("api_keys", "chat_chatgpt", [])
        self.api_base = sync_get_config("api_base", "chat_chatgpt", "")
        self.proxy = sync_get_config("proxy", "chat_chatgpt", "")
        self.model = sync_get_config("model", "chat_chatgpt", "gpt-3.5-turbo")
        self.temperature = sync_get_config("temperature", "chat_chatgpt", 0.4)
        self.max_tokens = sync_get_config("reply_max_tokens", "chat_chatgpt", 1024)
        self.top_p = sync_get_config("top_p", "chat_chatgpt", 1)
        self.frequency_penalty = sync_get_config(
            "frequency_penalty", "chat_chatgpt", 0.4
        )
        self.presence_penalty = sync_get_config("presence_penalty", "chat_chatgpt", 0.4)
        self.timeout = sync_get_config("timeout", "chat_chatgpt", 60)
        self.memory_short_length = sync_get_config(
            "memory_short_length", "chat_chatgpt", 12
        )
        self.memory_max_length = sync_get_config(
            "memory_max_length", "chat_chatgpt", 24
        )
        self.impression_length = sync_get_config(
            "impression_length", "chat_chatgpt", 20
        )
        self.impression_refresh_length = sync_get_config(
            "impression_refresh_length", "chat_chatgpt", 10
        )
        self.personality = sync_get_config(
            "personality", "chat_chatgpt", "她叫{bot_name}，是一个搭配师"
        )
        self.unlock_content = sync_get_config("unlock_content", "chat_chatgpt", False)
        self.max_response_per_msg = sync_get_config(
            "max_response_per_msg", "chat_chatgpt", 5
        )

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

    def _create_prompt_template(
        self,
        bot_name: str,
        user_name: str,
        impression: str,
        relative_plugin: str = None,
    ) -> ChatPromptTemplate:
        """创建聊天提示模板"""
        system_prompt = f"""
# Role: {bot_name}

## Profile
- language: 中文
- description: {self.personality}

## Skills

1. 核心技能
   - 对话: 与用户进行对话
   - 插件调用: 帮助用户使用插件

## Rules

1. 基本原则：
   - 回复内容严格遵循上下文信息，保持简洁
   - 以聊天为主进行互动，用户在明确需要时调用工具处理功能请求
   - 保持纯真自然且高度相关的表达方式

2. 行为准则：
   - 新需求优先查询工具适配情况
   - 群消息处理区分主动问候与设置指令
   - 文本回复需高度简洁，避免冗余信息与分段，严格减少总体文本量

3. 限制条件：
   - 严禁编造未提及的插件功能
   - 保持对话亲和力，避免专业术语
   - 保护用户隐私不泄露对话内容

## Workflows

- 目标: 高效调用插件并保持角色特色
- 步骤 1: 接收到指令时，优先处理用户聊天内容，若非聊天需求再分析工具调用需求
- 步骤 2: 只有在用户确实需要插件协助，并在明确表达需求的情况下，才使用trigger_plugin指令调用相关插件
- 步骤 3: 报告插件结果并附加必要补充信息；如果插件返回 "已成功调用该工具，工具结果已直接提供给用户，请勿再次调用"，则不报告结果，仅确认调用成功且无需再次操作
- 预期结果: 以简短形式输出功能调用与回应

### 附：当前可能相关插件
{relative_plugin}

## Initialization
作为{bot_name}，遵守上述Rules，按Workflows执行任务，确保回复关联度与简洁性。

当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %A')}
"""

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        return prompt

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
            message_content = await uniform_message(
                deserialize_message(chat.message), group_id=chat.group_id, bot=bot
            )
            if chat.target_id:  # 机器人回复
                if getattr(chat, "is_bot", False):
                    messages.append(AIMessage(content=message_content))
                else:
                    user_name = await get_user_name(
                        bot=bot, group_id=chat.group_id, user_id=chat.user_id
                    )
                    messages.append(
                        HumanMessage(content=f"{user_name}: {message_content}")
                    )
            else:
                user_name = await get_user_name(
                    bot=bot, group_id=chat.group_id, user_id=chat.user_id
                )
                messages.append(HumanMessage(content=f"{user_name}: {message_content}"))
        return messages

    async def _get_impression(self, bot: Bot, group_id: int, user_id: int) -> str:
        """获取用户印象"""
        impression = await ChatGPTChatImpression.filter(
            group_id=group_id, user_id=user_id, self_id=int(bot.self_id)
        ).first()

        if impression:
            bot_name = get_bot_name(bot=bot)
            user_name = await get_user_name(bot=bot, group_id=group_id, user_id=user_id)
            return impression.impression.format(user_name=user_name, bot_name=bot_name)
        return ""

    async def _update_impression(self, bot: Bot, group_id: int, user_id: int):
        """更新用户印象"""
        from tortoise.expressions import Q
        from tortoise.transactions import in_transaction

        self_id = int(bot.self_id)
        chat_history_user = (
            await ChatGPTChatHistory.filter(
                Q(group_id=group_id),
                Q(
                    Q(user_id=self_id, target_id=user_id),
                    Q(user_id=user_id, target_id=self_id),
                    join_type="OR",
                ),
            )
            .order_by("-time")
            .limit(self.impression_length)
        )

        if len(chat_history_user) < self.impression_length:
            return

        async with in_transaction() as connection:
            impression = (
                await ChatGPTChatImpression.filter(
                    group_id=group_id, user_id=user_id, self_id=self_id
                )
                .using_db(connection)
                .first()
            )
            if impression and (
                self.impression_refresh_length <= self.impression_length
            ):
                if (
                    impression.time
                    > chat_history_user[self.impression_refresh_length - 1].time
                ):
                    return
            if not impression:
                impression = ChatGPTChatImpression(
                    group_id=group_id,
                    user_id=user_id,
                    self_id=self_id,
                    impression="",
                )
                await impression.save(using_db=connection)

        user_name = await get_user_name(bot=bot, group_id=group_id, user_id=user_id)
        bot_name = get_bot_name(bot=bot)
        pre_impression = f"上次印象:{impression.impression.format(user_name=user_name,bot_name=bot_name) if impression else ''}\n\n"
        history_str = "\n".join(
            [await gen_chat_line(chat, bot) for chat in reversed(chat_history_user)]
        )

        prompt = f"""{pre_impression}[对话记录]
{history_str}

{self.personality.format(bot_name=bot_name)}
从{bot_name}的角度更新对{user_name}的印象:"""

        try:
            # 使用简单的LLM调用来生成印象，不使用agent
            impression_llm = self._create_llm()
            response = await impression_llm.ainvoke([HumanMessage(content=prompt)])

            impression.impression = response.content.replace(
                user_name, "{user_name}"
            ).replace(bot_name, "{bot_name}")
            await impression.save()
            logger.debug(f"更新印象成功: {impression.impression}")
        except Exception as e:
            logger.warning(f"生成对话印象失败：{e}")

    async def chat(
        self,
        matcher: Matcher,
        event: GroupMessageEvent,
        bot: Bot,
        trigger_text: List[Dict[str, Any]],
        sender_name: str,
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
                user_name = sender_name

                # 获取印象
                impression = await self._get_impression(
                    bot, event.group_id, event.user_id
                )

                # 获取聊天历史
                chat_history = await self._get_chat_history(thread_id, bot)

                uniformed_message = await uniform_message(
                    deserialize_message(trigger_text), group_id=event.group_id, bot=bot
                )

                # 获取相关插件
                relative_plugin = await search_plugin_tool(uniformed_message)

                # 创建提示模板
                prompt = self._create_prompt_template(
                    bot_name, user_name, impression, relative_plugin
                )

                # 每次根据最新 prompt 动态创建 agent
                agent = create_react_agent(self.llm, tools=self.tools, prompt=prompt)

                user_name = await get_user_name(
                    bot=bot, group_id=event.group_id, user_id=event.user_id
                )
                input_message = f"{user_name}: {uniformed_message}"
                # 组装 messages
                messages = chat_history + [HumanMessage(content=input_message)]

                # 流式处理响应
                import re
                import random
                import asyncio

                from langchain_core.messages import AIMessage
                from nonebot.adapters.onebot.v11 import Message

                buffer = ""
                count = 0
                sent_parts = []

                # 使用 agent 的流式输出，监听 AI 消息的增量内容
                async for chunk in agent.astream(
                    {"messages": messages},
                    stream_mode="messages",  # 改为 messages 模式
                ):
                    # chunk 是元组格式: (AIMessageChunk, metadata)
                    if isinstance(chunk, tuple) and len(chunk) >= 1:
                        message_chunk = chunk[0]
                        # 检查是否是 AI 消息且有内容
                        if (
                            isinstance(message_chunk, AIMessage)
                            and message_chunk.content
                        ):
                            # print(f"流式内容: {message_chunk.content}")
                            buffer += message_chunk.content

                        # 处理分段发送
                        while "*;" in buffer and count < self.max_response_per_msg:
                            part, buffer = buffer.split("*;", 1)
                            part = part.strip()
                            if part and not re.match(r"^[^\u4e00-\u9fa5\w]{1}$", part):
                                await matcher.send(Message(part))
                                await asyncio.sleep(random.random() + 1.5)
                                count += 1
                                sent_parts.append(part)
                        if count >= self.max_response_per_msg:
                            break

                # 发送剩余部分
                if buffer.strip() and count < self.max_response_per_msg:
                    await matcher.send(Message(buffer.strip()))
                    sent_parts.append(buffer.strip())
                if count >= self.max_response_per_msg:
                    logger.error(f"大模型回复内容过多，已截断")
                    await matcher.send(f"由于内容过多，麦克风被抢走了...")
                if sent_parts:
                    full_response_str = "*;".join(sent_parts)
                else:
                    full_response_str = buffer.strip()

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
                    message=serialize_message(full_response_str),
                    is_bot=True,  # 机器人消息
                ).save()

                # 更新印象
                # await self._update_impression(
                #     bot, getattr(event, "group_id", 0), event.user_id
                # )

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
