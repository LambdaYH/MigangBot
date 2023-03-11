from time import time
from enum import Enum, unique
from typing import Dict, List, Tuple, Optional

from nonebot.typing import T_State
from nonebot.plugin import PluginMetadata
from nonebot import on_command, on_fullmatch
from nonebot.params import Fullmatch, CommandArg
from tortoise.transactions import in_transaction
from tortoise.backends.base.client import BaseDBAsyncClient
from nonebot.adapters.onebot.v11 import (
    GROUP,
    Bot,
    Message,
    MessageSegment,
    GroupMessageEvent,
)

from migang.core.models import UserBag, UserProperty

from .data_source import TradeState, TradingStatus, draw_trade_window

__plugin_meta__ = PluginMetadata(
    name="交易系统",
    description="与群友完成一次愉快的交易吧",
    usage="""
usage：
    交易系统，与群友完成一次愉快的交易吧
    指令：
        交易 + @群友
        同意交易
        拒绝交易
        取消交易
        确认交易
        放置交易物品
    说明：
        【交易 + @群友】可发起交易，对方可发送【同意交易】或【拒绝交易】
        若同意交易则双方需发送【放置交易物品 xxx】放置物品，格式如下：
            放置交易物品 物品名1:数量 物品名2:数量（若需要放置金币，则物品名为金币）
        双方放置完后等待确认交易内容，可发送【确认交易】或【拒绝交易】

        任何时候发送取消交易都能取消当前交易
""".strip(),
    extra={
        "unique_name": "migang_user_trade",
        "example": "交易系统",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_category__ = "基础功能"

trading_timeout = 20 * 60


def check_timeout(user_id: int) -> bool:
    target_user = trading_pairs[user_id].target
    if (
        max(trading_pairs[user_id].start_time, trading_pairs[target_user].start_time)
        + trading_timeout
        < time()
    ):
        del trading_pairs[user_id]
        del trading_pairs[target_user]
        return False
    return True


@unique
class TradeState(Enum):
    INITIATOR = 0
    WAIT_FOR_ESTABLISH = 1
    WAIT_FOR_PUT_CONTENT = 2
    WAIT_FOR_CONFIRM = 3
    CONFIRMED = 4


class TradingStatus:
    def __init__(self, target: int, state: TradeState) -> None:
        self.target = target
        self.state: TradeState = state
        self.gold: int = 0
        self.items: List[Tuple[str, int]] = []
        self.start_time = time()


trading_pairs: Dict[int, TradingStatus] = {}


def check_establish_trade(event: GroupMessageEvent, state: T_State):
    target_user: Optional[int] = None
    for seg in event.message:
        if seg.type == "at":
            if target_user:
                return False  # 只能和一位对象交易
            else:
                target_user = seg.data["qq"]
    if not target_user:
        return False
    target_user = int(target_user)
    if target_user in trading_pairs:
        state["err"] = "对方存在一个尚未完成的交易"
        return True
    state["target"] = target_user
    return True


def check_response_trade(event: GroupMessageEvent, state: T_State):
    if event.user_id not in trading_pairs:
        return False
    if not check_timeout(event.user_id):
        state["err"] = "当前交易已过期"
        return True
    target_user = trading_pairs[event.user_id].target
    cmd = event.get_plaintext()[:2]
    if cmd == "同意":
        if trading_pairs[event.user_id].state != TradeState.WAIT_FOR_ESTABLISH:
            return False
    elif cmd == "拒绝":
        if (
            trading_pairs[event.user_id].state != TradeState.WAIT_FOR_ESTABLISH
            or trading_pairs[event.user_id].state != TradeState.WAIT_FOR_CONFIRM
        ):
            return False
    elif cmd == "确认":
        if trading_pairs[event.user_id].state != TradeState.WAIT_FOR_CONFIRM:
            return False
    state["target"] = target_user
    return True


def check_put_items(
    event: GroupMessageEvent,
    state: T_State,
):
    if event.user_id not in trading_pairs:
        return False
    if not check_timeout(event.user_id):
        state["err"] = "当前交易已过期"
        return True
    if trading_pairs[event.user_id].state != TradeState.WAIT_FOR_PUT_CONTENT:
        return False
    return True


establish_trade = on_command(
    "交易", priority=5, block=True, permission=GROUP, rule=check_establish_trade
)
state_confirm = on_fullmatch(
    ("同意交易", "拒绝交易", "取消交易", "确认交易"),
    priority=5,
    permission=GROUP,
    rule=check_response_trade,
)
put_item = on_command("放置交易物品", priority=5, permission=GROUP, rule=check_put_items)


async def check_stock(
    user_id: int, connection: Optional[BaseDBAsyncClient] = None
) -> List[str]:
    ret = []
    if (
        await UserProperty.get_gold(user_id=user_id, connection=connection)
    ) < trading_pairs[user_id].gold:
        ret.append("金币")
    for item in trading_pairs[user_id].items:
        if not await UserBag.check_item(
            user_id=user_id, item_name=item[0], amount=item[1], connection=connection
        ):
            ret.append(item[0])
    return ret


@establish_trade.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    if "err" in state:
        await establish_trade.finish(state["err"], at_sender=True)
    target_user = state["target"]
    trading_pairs[event.user_id] = TradingStatus(
        target_user, state=TradeState.INITIATOR
    )
    trading_pairs[target_user] = TradingStatus(
        event.user_id, state=TradeState.WAIT_FOR_ESTABLISH
    )
    member_info = await bot.get_group_member_info(
        group_id=event.group_id, user_id=target_user
    )
    nickname = member_info.get("card") or member_info.get("nickname")
    await establish_trade.send(
        f"已申请与 {nickname}({target_user}) 置换道具，等待对方响应（发送 同意交易）", at_sender=True
    )


@state_confirm.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State, cmd: str = Fullmatch()):
    if "err" in state:
        await state_confirm.finish(state["err"], at_sender=True)
    target_user = state["target"]
    member_info = await bot.get_group_member_info(
        group_id=event.group_id, user_id=target_user
    )
    nickname = member_info.get("card") or member_info.get("nickname")
    cmd = cmd[:2]
    if cmd == "同意":
        trading_pairs[event.user_id].state = TradeState.WAIT_FOR_PUT_CONTENT
        trading_pairs[target_user].state = TradeState.WAIT_FOR_PUT_CONTENT
        trading_pairs[event.user_id].start_time = time()
        trading_pairs[target_user].start_time = time()
        await state_confirm.finish(
            f"已建立与 {nickname}({target_user}) 的交易，请双方发送 [放置交易物品 物品名1:数量 物品名2:数量] 放置物品，具体可查看帮助",
            at_sender=True,
        )
    if cmd == "拒绝" or cmd == "取消":
        del trading_pairs[target_user]
        del trading_pairs[event.user_id]
        await state_confirm.finish(
            f"与 {nickname}({target_user}) 的交易已取消", at_sender=True
        )
    if cmd == "确认":
        trading_pairs[event.user_id].state = TradeState.CONFIRMED
        trading_pairs[event.user_id].start_time = time()
        trading_pairs[target_user].start_time = time()
        if trading_pairs[target_user].state == TradeState.CONFIRMED:
            async with in_transaction() as connection:
                # 先再次检查
                if ret := (await check_stock(event.user_id, connection=connection)):
                    del trading_pairs[event.user_id]
                    del trading_pairs[target_user]
                    await state_confirm.finish(
                        f"{event.sender.card or event.sender.nickname}({event.user_id}) 背包中的 "
                        + "/".join(ret)
                        + "数量不足，交易终止！"
                    )
                if ret := (await check_stock(target_user, connection=connection)):
                    del trading_pairs[event.user_id]
                    del trading_pairs[target_user]
                    await state_confirm.finish(
                        f"{nickname}({target_user}) 背包中的 "
                        + "/".join(ret)
                        + "数量不足，交易终止！"
                    )

                # 如果这段间隙间还飞快地把交易道具用掉了，那我也暂时没办法（懒得管

                # 先扣掉要交易走的
                await UserProperty.modify_gold(
                    user_id=event.user_id,
                    gold_diff=-trading_pairs[event.user_id].gold,
                    description=f"与 {nickname}({target_user}) 的交易付出",
                    connection=connection,
                )
                await UserProperty.modify_gold(
                    user_id=target_user,
                    gold_diff=-trading_pairs[target_user].gold,
                    description=f"与 {event.sender.card or event.sender.nickname}({event.user_id}) 的交易付出",
                    connection=connection,
                )
                for item in trading_pairs[event.user_id].items:
                    await UserBag.del_item(
                        user_id=event.user_id,
                        item_name=item[0],
                        amount=item[1],
                        connection=connection,
                    )
                for item in trading_pairs[target_user].items:
                    await UserBag.del_item(
                        user_id=target_user,
                        item_name=item[0],
                        amount=item[1],
                        connection=connection,
                    )
                # 开始给东西
                await UserProperty.modify_gold(
                    user_id=event.user_id,
                    gold_diff=trading_pairs[target_user].gold,
                    description=f"与 {nickname}({target_user}) 的交易获得",
                    connection=connection,
                )
                await UserProperty.modify_gold(
                    user_id=target_user,
                    gold_diff=trading_pairs[event.user_id].gold,
                    description=f"与 {event.sender.card or event.sender.nickname}({event.user_id}) 的交易获得",
                    connection=connection,
                )
                for item in trading_pairs[event.user_id].items:
                    await UserBag.add_item(
                        user_id=target_user,
                        item_name=item[0],
                        amount=item[1],
                        connection=connection,
                    )
                for item in trading_pairs[target_user].items:
                    await UserBag.add_item(
                        user_id=event.user_id,
                        item_name=item[0],
                        amount=item[1],
                        connection=connection,
                    )
                await state_confirm.send(
                    f"{nickname}({target_user}) 与 {event.sender.card or event.sender.nickname}({event.user_id})的交易完成了！"
                )
        else:
            await state_confirm.finish(
                f"请等待 {nickname}({target_user}) 确认交易", at_sender=True
            )


@put_item.handle()
async def _(
    bot: Bot,
    event: GroupMessageEvent,
    state: T_State,
    args: Message = CommandArg(),
):
    if "err" in state:
        await establish_trade.finish(state["err"], at_sender=True)
    args = args.extract_plain_text().strip().split(" ")
    trading_pairs[event.user_id].start_time = time()
    user_bag = await UserBag.get_item_list(user_id=event.user_id)
    for arg in args:
        arg = arg.strip().split(":")
        if len(arg) != 2:
            continue
        if arg[0] == "gold" or arg[0] == "金币":
            if not arg[1].isdigit():
                trading_pairs[event.user_id].gold = 0
                trading_pairs[event.user_id].items.clear()
                await put_item.finish("金币的数量不正确！请重新放置物品")

            trading_pairs[event.user_id].gold += int(arg[1])
        else:
            if arg[0].isdigit():
                idx = int(arg[0])
                if arg[0] <= 0 or arg[0] > len(user_bag):
                    await put_item.finish(f"不存在序号为 {idx} 的物品，请检查背包")
                arg[0] = user_bag[idx].item_name
            if not arg[1].isdigit():
                trading_pairs[event.user_id].gold = 0
                trading_pairs[event.user_id].items.clear()
                await put_item.finish(f"物品 {arg[0]} 的数量不正确！请重新放置物品")
            trading_pairs[event.user_id].items.append((arg[0], int(arg[1])))
    async with in_transaction() as connection:
        ret = await check_stock(user_id=event.user_id, connection=connection)
    if ret:
        trading_pairs[event.user_id].gold = 0
        trading_pairs[event.user_id].items.clear()
        await put_item.finish("背包中的 " + "/".join(ret) + " 数量不足，请重新放置物品")
    trading_pairs[event.user_id].state = TradeState.WAIT_FOR_CONFIRM
    trading_pairs[event.user_id].start_time = time()
    target_user = trading_pairs[event.user_id].target
    member_info = await bot.get_group_member_info(
        group_id=event.group_id, user_id=target_user
    )
    nickname = member_info.get("card") or member_info.get("nickname")
    if trading_pairs[target_user].state == TradeState.WAIT_FOR_CONFIRM:
        await put_item.send(
            f"以下为 {nickname}({target_user}) 与 {event.sender.card or event.sender.nickname}({event.user_id}) 的交易内容，若确认请双方发送 确认交易，反之则发送 拒绝交易"
            + MessageSegment.image(
                await draw_trade_window(
                    (target_user, trading_pairs[target_user]),
                    (event.user_id, trading_pairs[event.user_id].gold),
                )
            )
        )
    else:
        await put_item.finish(f"物品放置成功，请等待 {nickname}({target_user}) 完成放置")
