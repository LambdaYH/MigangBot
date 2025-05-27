from typing import Tuple
from datetime import datetime

from nonebot.log import logger
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from migang.core import sync_get_config
from migang.core.models import ChatGPTChatHistory

from .utils import get_bot_name, gen_chat_text, get_user_name, serialize_message


async def pre_check(event: GroupMessageEvent, bot: Bot, state: T_State) -> bool:
    sender_name = await get_user_name(
        bot=bot, group_id=event.group_id, user_id=event.user_id
    )
    plain_text = event.get_plaintext()
    if not plain_text:
        logger.debug("空消息，不处理")
        return False
    if plain_text.startswith(ignore_prefix):
        logger.debug("忽略消息前缀")
        return False
    chat_text, is_tome = await gen_chat_text(event=event, bot=bot)
    is_tome = is_tome or event.is_tome()
    bot_name = get_bot_name(bot=bot)

    # 是否需要响应
    triggered = is_tome or (bot_name.lower() in chat_text.lower())

    # 记录消息，虽然可能与我无关，但是记录保证对上下文的理解
    record_msg = serialize_message(event.message)
    if is_tome:
        record_msg = [
            {"type": "at", "data": {"qq": bot.self_id}},
            {"type": "text", "data": {"text": " "}},
        ] + record_msg
    await ChatGPTChatHistory(
        user_id=event.user_id,
        group_id=event.group_id,
        target_id=event.self_id if triggered else None,
        message=record_msg,
        is_bot=False,  # 用户消息
    ).save()

    if triggered:
        logger.debug("符合发言条件，开始回复")
        # 保存信息，用于回复
        state["gpt_sender_name"] = sender_name
        state["gpt_trigger_text"] = chat_text
    return triggered


async def do_chat(
    matcher: Matcher, event: GroupMessageEvent, bot: Bot, state: T_State
) -> None:
    trigger_text = state["gpt_trigger_text"]
    sender_name = state["gpt_sender_name"]

    start_time = datetime.now()

    # 使用新的langchain实现
    from .langchain_chat import langchain_chatbot

    await langchain_chatbot.chat(matcher, event, bot, trigger_text, sender_name)

    logger.debug(f"对话响应完成 | 耗时: {(datetime.now() - start_time).seconds}s")
