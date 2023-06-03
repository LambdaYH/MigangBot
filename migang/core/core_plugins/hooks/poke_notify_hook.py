"""单独处理poke，因为私聊和群聊都有poke
"""
from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException
from nonebot.adapters.onebot.v11 import PokeNotifyEvent

from migang.core.manager import user_manager, group_manager

from .utils import check_event


@run_preprocessor
async def _(
    matcher: Matcher,
    event: PokeNotifyEvent,
):
    if event.group_id is not None:
        if not group_manager.check_group_plugin_status(
            plugin_name=matcher.plugin_name, group_id=event.group_id
        ):
            raise IgnoredException("群插件不可用")
    if not user_manager.check_user_plugin_status(
        plugin_name=matcher.plugin_name, user_id=event.user_id
    ):
        raise IgnoredException("个人权限不足或插件未启用")
    await check_event(matcher=matcher, event=event)
