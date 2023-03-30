from typing import cast

from nonebot.adapters import Message, MessageSegment
from nonebot.adapters.onebot.v11 import Message as OneBotV11Message
from nonebot.adapters.onebot.v12 import Message as OneBotV12Message
from nonebot.params import CommandArg
from pydantic import BaseModel

def strtobool(val: str) -> bool:
    """将文本转化成布尔值

    如果是 y, yes, t, true, on, 1, 是, 确认, 开, 返回 True;
    其他的均为返回 False;
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1", "是", "确认", "开"):
        return True
    return False

class MentionedUser(BaseModel):
    id: str
    segment: MessageSegment


async def get_mentioned_user(args: Message = CommandArg()) -> MentionedUser | None:
    """获取提到的用户信息"""
    if isinstance(args, OneBotV11Message) and (at := args["at"]):
        at = at[0]
        at = cast(MessageSegment, at)
        return MentionedUser(id=at.data["qq"], segment=at)
    if isinstance(args, OneBotV12Message) and (mention := args["mention"]):
        mention = mention[0]
        mention = cast(MessageSegment, mention)
        return MentionedUser(id=mention.data["user_id"], segment=mention)