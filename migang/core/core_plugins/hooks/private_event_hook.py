from typing import Union

from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException
from nonebot.adapters.onebot.v11 import (
    PrivateMessageEvent,
    FriendAddNoticeEvent,
    FriendRecallNoticeEvent,
    FriendRequestEvent,
    GroupRequestEvent,
)

from migang.core.manager import (
    user_manager,
    cd_manager,
    count_manager,
)
from migang.core.models import NickName


@run_preprocessor
async def _(
    matcher: Matcher,
    event: Union[
        PrivateMessageEvent,
        FriendAddNoticeEvent,
        FriendRecallNoticeEvent,
        FriendRequestEvent,
        GroupRequestEvent,
    ],
):
    if not user_manager.CheckUserPluginStatus(
        plugin_name=matcher.plugin_name, user_id=event.user_id
    ):
        raise IgnoredException("个人权限不足或插件未启用")
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
    if name := await NickName.filter(user_id=event.user_id).first():
        event.sender.nickname = name.nickname