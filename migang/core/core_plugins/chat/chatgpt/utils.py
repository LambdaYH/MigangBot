from typing import Tuple
from functools import cache

from aiocache import cached
from nonebot import require
from nonebot.adapters import Bot, Event, Message
from nonebot_plugin_userinfo import get_user_info
from nonebot_plugin_alconna import At, Text, AtAll, UniMessage

from migang.core.models import ChatGPTChatHistory

require("nonebot_plugin_chatrecorder")
from nonebot_plugin_chatrecorder import deserialize_message


@cache
def get_bot_name(bot: Bot) -> str:
    return list(bot.config.nickname)[0]


async def get_user_name(bot: Bot, event: Event, user_id: str) -> str:
    """
    Args:
        bot (Bot): _description_
        group_id (int): _description_
        user_id (int): _description_

    Returns:
        str: _description_
    """
    if event.get_user_id() == bot.self_id:
        return get_bot_name(bot)

    user_info = await get_user_info(bot=bot, event=event, user_id=user_id)
    if user_info is None:
        return f"未知_{event.get_user_id()}"
    return user_info.user_name


async def uniform_message(message: Message, event: Event, bot: Bot) -> str:
    message = await UniMessage.generate(message=message, event=event, bot=bot)
    msg = ""
    for seg in message:
        if isinstance(seg, Text):
            msg += seg.text
        elif isinstance(seg, AtAll):
            msg += "@全体成员"
        elif isinstance(seg, At):
            user_name = await get_user_name(bot, event, seg.target)
            if user_name:
                msg += f"@{user_name}"  # 保持给bot看到的内容与真实用户看到的一致
    return msg


async def gen_chat_text(
    message: UniMessage, event: Event, bot: Bot
) -> Tuple[str, bool]:
    """生成合适的会话消息内容(eg. 将cq at 解析为真实的名字)"""
    wake_up = message.has(At)
    return (
        await uniform_message(message=message, event=event, bot=bot),
        wake_up,
    )


async def gen_chat_line(
    chat_history: ChatGPTChatHistory, bot: Bot, event: Event
) -> str:
    return f"[{chat_history.time.astimezone().strftime('%H:%M:%S %p')}] {await get_user_name(event=event, user_id=chat_history.user_id, bot=bot)}: {await uniform_message(deserialize_message(bot, chat_history.message), event=event, bot=bot)}"
