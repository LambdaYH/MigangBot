from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException
from nonebot.adapters.onebot.v11 import GroupMessageEvent

from migangbot.core.manager import group_manager


@run_preprocessor
async def _(matcher: Matcher, event: GroupMessageEvent):
    if type(event) is GroupMessageEvent and not group_manager.CheckGroupPluginStatus(
        plugin_name=matcher.plugin_name, group_id=event.group_id
    ):
        raise IgnoredException("群插件不可用")
