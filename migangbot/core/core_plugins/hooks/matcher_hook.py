from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException
from nonebot.adapters.onebot.v11 import (
    Event,
    Bot,
    MessageEvent,
    PokeNotifyEvent,
    GroupMessageEvent,
)

from migangbot.core.manager import group_manager, cd_manager, count_manager


@run_preprocessor
async def _(bot: Bot, matcher: Matcher, event: Event):
    # 检测群插件启用情况
    if type(event) is GroupMessageEvent and not group_manager.CheckGroupPluginStatus(
        plugin_name=matcher.plugin_name, group_id=event.group_id
    ):
        raise IgnoredException("群插件不可用")
    if isinstance(event, MessageEvent) or type(event) is PokeNotifyEvent:
        # 检测插件CD
        if (
            ret := cd_manager.Check(plugin_name=matcher.plugin_name, event=event)
        ) != True:
            await matcher.send(ret)
            raise IgnoredException("cd...")
        # 检查插件次数限制
        if (
            ret := count_manager.Check(plugin_name=matcher.plugin_name, event=event)
        ) != True:
            await matcher.send(ret)
            raise IgnoredException("count...")
