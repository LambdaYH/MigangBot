from functools import cache
from typing import Any, Dict, List, Tuple

from aiocache import cached
from pydantic import parse_obj_as
from nonebot.adapters.onebot.v11 import Bot, Message, ActionFailed, GroupMessageEvent

from migang.core.models import ChatGPTChatHistory


@cache
def get_bot_name(bot: Bot) -> str:
    return list(bot.config.nickname)[0]


@cached(ttl=20 * 60)
async def get_user_name(bot: Bot, group_id: int, user_id: int) -> str:
    """获取用户昵称，缓存20分钟

    Args:
        bot (Bot): _description_
        group_id (int): _description_
        user_id (int): _description_

    Returns:
        str: _description_
    """
    if user_id == int(bot.self_id):
        return get_bot_name(bot)
    try:
        user_info = await bot.get_group_member_info(
            group_id=group_id, user_id=user_id, no_cache=False
        )
        user_name = user_info.get("card") or user_info["nickname"]
        return user_name
    except ActionFailed:
        return "未知"


def serialize_message(message: Message | str) -> List[Dict[str, Any]]:
    if isinstance(message, str):
        message = Message(message)
    return [seg.__dict__ for seg in message if seg.type == "text" or seg.type == "at"]


def deserialize_message(message: List[Dict[str, Any]]) -> Message:
    return parse_obj_as(Message, message)


async def uniform_message(message: Message, group_id: int, bot: Bot) -> str:
    msg = ""
    for seg in message:
        if seg.is_text():
            msg += seg.data.get("text", "")
        elif seg.type == "at":
            qq = seg.data.get("qq", None)
            if qq:
                if qq == "all":
                    msg += "@全体成员"
                elif qq == bot.self_id:
                    msg += f"@{get_bot_name(bot)}"
                else:
                    user_name = await get_user_name(
                        bot=bot, group_id=group_id, user_id=int(qq)
                    )
                    if user_name:
                        msg += f"@{user_name}"  # 保持给bot看到的内容与真实用户看到的一致
    return msg


async def gen_chat_text(event: GroupMessageEvent, bot: Bot) -> Tuple[str, bool]:
    """生成合适的会话消息内容(eg. 将cq at 解析为真实的名字)"""
    wake_up = False
    for seg in event.message:
        if seg.type == "at" and seg.data["qq"] == "all":
            wake_up = True
            break
    return (
        await uniform_message(message=event.message, group_id=event.group_id, bot=bot),
        wake_up,
    )


async def gen_chat_line(chat_history: ChatGPTChatHistory, bot: Bot) -> str:
    print(chat_history.time.astimezone().strftime("%H:%M:%S %p"))
    return f"[{chat_history.time.astimezone().strftime('%H:%M:%S %p')}] {await get_user_name(group_id=chat_history.group_id,user_id=chat_history.user_id, bot=bot)}: {await uniform_message(deserialize_message(chat_history.message), group_id=chat_history.group_id, bot=bot)}"
