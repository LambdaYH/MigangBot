from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from ..exception import BreakSession
from .naturel_gpt.matcher import handler


async def get_gpt_chat(matcher: Matcher, event: GroupMessageEvent, bot: Bot):
    await handler(matcher_=matcher, event=event, bot=bot)
    raise BreakSession("由naturel_gpt处理发送逻辑")
