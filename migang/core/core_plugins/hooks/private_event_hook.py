from typing import Union

from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, FriendRecallNoticeEvent

from migang.core.manager import user_manager

from .utils import check_event


@run_preprocessor
async def _(
    matcher: Matcher,
    event: Union[
        PrivateMessageEvent,
        FriendRecallNoticeEvent,
    ],
):
    if not user_manager.check_user_plugin_status(
        plugin_name=matcher.plugin_name, user_id=event.user_id
    ):
        raise IgnoredException("个人权限不足或插件未启用")
    await check_event(matcher=matcher, event=event)
