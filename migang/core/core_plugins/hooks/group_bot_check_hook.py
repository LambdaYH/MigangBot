from typing import Union

from nonebot import get_bots
from nonebot.exception import IgnoredException
from nonebot.message import event_preprocessor
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageSegment,
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
    if event.get_user_id() in get_bots():
        raise IgnoredException("发抖")


@event_preprocessor
async def _(
    bot: Bot,
    event: GroupMessageEvent,
):
    # 过滤机器人发的消息
    if event.get_user_id() in get_bots():
        raise IgnoredException("发抖")
    # 检查群机器人
    if group_bot_manager.check_group_bot(event.group_id, event.self_id):
        # 如果是群机器人，直接响应
        return
    # 如果不是群机器人，检查是否@自己，喊名字的不响应，@的响应
    if event.is_tome():
        for seg in event.original_message:
            if seg.type == "at" and seg.data.get("qq") == bot.self_id:
                return
    raise IgnoredException("躺~")
