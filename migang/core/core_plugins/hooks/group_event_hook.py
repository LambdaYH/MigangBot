from typing import Union

from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException
from nonebot.adapters.onebot.v11 import (
    PokeNotifyEvent,
    GroupMessageEvent,
)

from migang.core.manager import (
    group_manager,
    cd_manager,
    count_manager,
)
from migang.core.models import NickName

_ignore_plugins = set(["switch_bot"])


@run_preprocessor
async def _(matcher: Matcher, event: Union[GroupMessageEvent, PokeNotifyEvent]):
    if matcher.plugin_name in _ignore_plugins:
        return
    # 检测群插件启用情况
    if not group_manager.check_group_plugin_status(
        plugin_name=matcher.plugin_name, group_id=event.group_id
    ):
        raise IgnoredException("群插件不可用")
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
    # 检查通过后把事件的sender昵称替换为昵称系统昵称
    if name := await NickName.filter(user_id=event.user_id).first():
        event.sender.nickname = name.nickname
