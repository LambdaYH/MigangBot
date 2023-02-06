from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException
from nonebot.adapters.onebot.v11 import PrivateMessageEvent

from migangbot.core.manager import (
    user_manager,
    cd_manager,
    count_manager,
)


@run_preprocessor
async def _(matcher: Matcher, event: PrivateMessageEvent):
    if not user_manager.CheckUserPluginStatus(
        plugin_name=matcher.plugin_name, user_id=event.user_id
    ):
        raise IgnoredException("个人权限不足或插件未启用")
    # 检测插件CD
    if (ret := cd_manager.check(plugin_name=matcher.plugin_name, event=event)) != True:
        await matcher.send(ret)
        raise IgnoredException("cd...")
    # 检查插件次数限制
    if (
        ret := count_manager.check(plugin_name=matcher.plugin_name, event=event)
    ) != True:
        await matcher.send(ret)
        raise IgnoredException("count...")
