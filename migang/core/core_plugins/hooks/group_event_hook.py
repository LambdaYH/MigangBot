from typing import Union

from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    GroupBanNoticeEvent,
    GroupAdminNoticeEvent,
    GroupRecallNoticeEvent,
    GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent,
)

from migang.core.manager import user_manager, group_manager

from .utils import check_event

_ignore_plugins = set(["switch_bot"])


@run_preprocessor
async def _(
    matcher: Matcher,
    event: Union[
        GroupMessageEvent,
        GroupAdminNoticeEvent,
        GroupBanNoticeEvent,
        GroupDecreaseNoticeEvent,
        GroupIncreaseNoticeEvent,
        GroupRecallNoticeEvent,
    ],
):
    if matcher.plugin_name in _ignore_plugins:
        return
    if not group_manager.check_group_plugin_status(
        plugin_name=matcher.plugin_name, group_id=event.group_id
    ):
        raise IgnoredException("群插件不可用")
    # 检测个人权限
    if not user_manager.check_user_plugin_status(
        plugin_name=matcher.plugin_name, user_id=event.user_id
    ):
        raise IgnoredException("个人权限不足")
    await check_event(matcher=matcher, event=event)
