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
    GROUP,
)
from time import time
from typing import Optional, List, Tuple, Dict
import anyio
from enum import Enum, unique
from tortoise.transactions import in_transaction

from migang.core.manager import goods_manager
from migang.core.manager.goods_manager import UseStatus, GoodsHandlerParams
from migang.core.models import UserBag, UserProperty, TransactionLog

__plugin_meta__ = PluginMetadata(
    name="商店",
    description="商店",
    usage="""
usage：
    签到，数据以用户为单位
    指令：
        签到
""".strip(),
    extra={
        "unique_name": "migang_shop",
        "example": "签到",
        "author": "migang",
        "version": 0.1,
    },
)

trading_timeout = 20 * 60

@unique
class TradeState(Enum):
    WAIT_FOR_ESTABLISH = 0
    WAIT_FOR_PUT_CONTENT = 1
    WAIT_FOR_CONFIRM = 2
    CONFIRMED = 3


class TradingStatus:
    def __init__(self, target: int) -> None:
        self.target = target
        self.state: TradeState = TradeState.WAIT_FOR_ESTABLISH
        self.gold: int = 0
        self.items: List[Tuple[str, int]] = []
        self.start_time = time()


trading_pairs: Dict[int, TradingStatus] = {}


def check_establish_trade(event: GroupMessageEvent, state: T_State):
    target_user: Optional[int] = None
    for seg in event.msg:
        if seg.type == "at":
            if target_user:
                return False  # 只能和一位对象交易
            else:
                target_user = seg.data["qq"]
    if not target_user:
        return False
    state["target"] = target_user
    return True


def check_response_trade(event: GroupMessageEvent):
    if event.user_id not in trading_pairs:
        return False
    cmd = event.get_plaintext()[:1]
    if cmd == "同意":
        if trading_pairs[event.user_id].state != TradeState.WAIT_FOR_ESTABLISH:
            return False
        target_user = trading_pairs[event.user_id].target
        trading_pairs[event.user_id].state = TradeState.WAIT_FOR_PUT_CONTENT
        trading_pairs[target_user].state = TradeState.WAIT_FOR_PUT_CONTENT
    elif cmd == "拒绝":
        if trading_pairs[event.user_id].state != TradeState.WAIT_FOR_ESTABLISH:
            return False
        target_user = trading_pairs[event.user_id].target
        del trading_pairs[target_user]
        del trading_pairs[event.user_id]
    elif cmd == "取消":
        target_user = trading_pairs[event.user_id].target
        del trading_pairs[target_user]
        del trading_pairs[event.user_id]
    elif cmd == "确认":
        if trading_pairs[event.user_id].state != TradeState.WAIT_FOR_CONFIRM:
            return False
        trading_pairs[event.user_id].state = TradeState.CONFIRMED


establish_trade = on_command(
    "交易", priority=5, block=True, permission=GROUP, rule=check_establish_trade
)
state_confirm = on_fullmatch(
    ("同意交易", "拒绝交易", "取消交易", "确认交易"),
    permission=GROUP,
)


@establish_trade.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    target_user = state["target"]
    if target_user in trading_pairs:
        await establish_trade("对方存在一个尚未完成的交易", at_sender=True)
    trading_pairs[event.user_id] = TradingStatus(target_user)
    trading_pairs[target_user] = TradingStatus(event.user_id)
    member_info = await bot.get_group_member_info(
        group_id=event.group_id, user_id=target_user
    )
    nickname = member_info.get("card") or member_info.get("nickname")
    await establish_trade.send(
        f"已申请与 {nickname}({target_user}) 置换道具，等待对方响应", at_sender=True
    )
