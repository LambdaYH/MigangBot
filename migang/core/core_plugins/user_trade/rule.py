from nonebot.plugin import PluginMetadata
from nonebot import on_fullmatch, on_startswith, on_command, on_message
from nonebot.params import Startswith, CommandArg
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    MessageEvent,
    GroupMessageEvent,
    Bot,
    Message,
    GROUP
)
from typing import Optional
import anyio
from tortoise.transactions import in_transaction

from migang.core.manager import goods_manager
from migang.core.manager.goods_manager import UseStatus, GoodsHandlerParams
from migang.core.models import UserBag, UserProperty, TransactionLog



def check_trade_condition(event: GroupMessageEvent, state: T_State):
    target_user:Optional[int] = None
    for seg in event.msg:
        if seg.type == 'at':
            if target_user:
                return False # 只能和一位对象交易
            else:
                target_user = seg.data["qq"]
    if not target_user:
        return False
    state['target'] = target_user
    return True

def check_trade_user(event: GroupMessageEvent, state: T_State):
