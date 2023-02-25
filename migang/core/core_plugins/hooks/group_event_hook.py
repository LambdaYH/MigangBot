from typing import Union

from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException
from nonebot.adapters.onebot.v11 import (
    PokeNotifyEvent,
    GroupMessageEvent,
    GroupBanNoticeEvent,
    GroupAdminNoticeEvent,
    GroupRecallNoticeEvent,
    GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent,
)

from migang.core.models import UserProperty
from migang.core.manager import cd_manager, user_manager, count_manager, group_manager

_ignore_plugins = set(["switch_bot"])


@run_preprocessor
async def _(
    matcher: Matcher,
    event: Union[
        GroupMessageEvent,
        PokeNotifyEvent,
        GroupAdminNoticeEvent,
        GroupBanNoticeEvent,
        GroupDecreaseNoticeEvent,
        GroupIncreaseNoticeEvent,
        GroupRecallNoticeEvent,
    ],
):
    if matcher.plugin_name in _ignore_plugins:
        return
    # 检测群插件启用情况以及群权限
    if not group_manager.check_group_plugin_status(
        plugin_name=matcher.plugin_name, group_id=event.group_id
    ):
        raise IgnoredException("群插件不可用")
    # 检测个人权限
    if not user_manager.check_user_plugin_status(
        plugin_name=matcher.plugin_name, user_id=event.user_id
    ):
        raise IgnoredException("个人权限不足")
    # 检测插件CD
    if (ret := cd_manager.check(plugin_name=matcher.plugin_name, event=event)) != True:
        if ret != None:
            await matcher.send(ret)
        raise IgnoredException("cd...")
    # 检查插件次数限制
    if (
        ret := count_manager.check(plugin_name=matcher.plugin_name, event=event)
    ) != True:
        if ret != None:
            await matcher.send(ret)
        raise IgnoredException("count...")
    # 检查通过后把事件的sender昵称替换为昵称系统昵称
    if (
        hasattr(event, "sender")
        and (
            name := await UserProperty.filter(user_id=event.user_id)
            .first()
            .values_list("nickname")
        )
        and (name[0] is not None)
    ):
        event.sender.nickname = name[0]
