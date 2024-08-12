from typing import Union

from nonebot.exception import IgnoredException
from nonebot.message import event_preprocessor
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    GroupBanNoticeEvent,
    GroupAdminNoticeEvent,
    GroupRecallNoticeEvent,
    GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent,
)

from migang.core.manager import group_bot_manager


@event_preprocessor
async def _(
    event: Union[
        GroupMessageEvent,
        GroupAdminNoticeEvent,
        GroupBanNoticeEvent,
        GroupDecreaseNoticeEvent,
        GroupIncreaseNoticeEvent,
        GroupRecallNoticeEvent,
    ],
):
    # 群机器人检查
    if not group_bot_manager.check_group_bot(event.group_id, event.self_id):
        raise IgnoredException("躺~")
