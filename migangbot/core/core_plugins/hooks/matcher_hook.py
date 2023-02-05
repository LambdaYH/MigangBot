from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException
from nonebot.adapters.onebot.v11 import (
    Event,
    MessageEvent,
    PokeNotifyEvent,
    GroupMessageEvent,
    PrivateMessageEvent,
)

from migangbot.core.manager import (
    group_manager,
    user_manager,
    cd_manager,
    count_manager,
)

_ignore_plugins = set(["switch_bot"])


@run_preprocessor
async def _(matcher: Matcher, event: Event):
    if matcher.plugin_name in _ignore_plugins:
        return
    # 检测群插件启用情况
    if type(event) is GroupMessageEvent and not group_manager.check_group_plugin_status(
        plugin_name=matcher.plugin_name, group_id=event.group_id
    ):
        raise IgnoredException("群插件不可用")
    if type(event) is PrivateMessageEvent and not user_manager.CheckUserPluginStatus(
        plugin_name=matcher.plugin_name, user_id=event.user_id
    ):
        raise IgnoredException("个人权限不足或插件未启用")
    if isinstance(event, MessageEvent) or type(event) is PokeNotifyEvent:
        # 检测插件CD
        if (
            ret := cd_manager.check(plugin_name=matcher.plugin_name, event=event)
        ) != True:
            await matcher.send(ret)
            raise IgnoredException("cd...")
        # 检查插件次数限制
        if (
            ret := count_manager.check(plugin_name=matcher.plugin_name, event=event)
        ) != True:
            await matcher.send(ret)
            raise IgnoredException("count...")
