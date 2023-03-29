from migang.core.manager import config_manager, ConfigItem
from nonebot.adapters.onebot.v11 import GroupMessageEvent,Bot
from nonebot.matcher import Matcher

from .naturel_gpt.matcher import handler
from ..exception import BreakSession

async def get_gpt_chat(matcher:Matcher, event: GroupMessageEvent, bot:Bot):
    await handler(matcher_=matcher, event=event, bot=bot)
    raise BreakSession("由naturel_gpt处理发送逻辑")