from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.exception import FinishedException
from tortoise.transactions import in_transaction
from nonebot.params import CommandArg, Startswith
from nonebot import on_command, on_fullmatch, on_startswith
from nonebot.adapters.onebot.v11 import (
    Bot,
    Message,
    MessageEvent,
    MessageSegment,
    GroupMessageEvent,
)

from migang.core.manager import goods_manager
from migang.core.manager.goods_manager import UseStatus, GoodsHandlerParams
from migang.core.models import (
    ShopLog,
    UserBag,
    ShopGroupLog,
    UserProperty,
    TransactionLog,
)

from .bag import draw_bag
from .shop import draw_shop
from . import default_goods  # noqa
from .shop_control import adjust_goods, adjust_goods_group

__plugin_meta__ = PluginMetadata(
    name="商店",
    description="商店",
    usage="""
usage：
    指令：
        商店
        购买道具 商品名/序号
        我的背包
        使用道具 道具名/序号

    超级用户指令：
        （懒得写）
        修改商品 goods:商品名 设置名:参数
        修改商品 group:组名 设置名:参数
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

__plugin_category__ = "基础功能"

show_shop = on_fullmatch("商店", priority=5, block=True)
buy = on_startswith("购买道具", priority=5, block=True)
my_bag = on_fullmatch(("我的道具", "我的背包", "我的金币"), priority=5, block=True)
use = on_startswith("使用道具", priority=5, block=True)

give_gold = on_command("给他打钱", permission=SUPERUSER, priority=5, block=False)
modify = on_startswith("修改商品", priority=5, permission=SUPERUSER, block=True)


@show_shop.handle()
async def _():
    await show_shop.send(MessageSegment.image(await draw_shop()))


@buy.handle()
async def _(event: MessageEvent, cmd: str = Startswith()):
    args = event.get_plaintext().removeprefix(cmd).split(" ")
    amount: int
    if len(args) == 2:
        args[1] = args[1].strip()
        if not args[1].isdigit():
            await buy.finish("购买数量必须为正整数", at_sender=True)
        amount = int(args[1])
        if amount <= 0:
            await buy.finish("购买数量必须为正整数", at_sender=True)
    else:
        amount = 1
    name = args[0].strip()
    if name.isdigit():
        name = int(name) - 1
    goods = goods_manager.get_goods(name=name)
    if not goods:
        await buy.finish("不存在该商品", at_sender=True)

    async with in_transaction() as connection:
        user_prop = (
            await UserProperty.filter(user_id=event.user_id)
            .using_db(connection)
            .first()
        )
        price = int(goods.price * goods.discount)
        if not user_prop and price != 0:
            await buy.finish("金币不足！")
        if price != 0:
            if goods.purchase_limit:
                today_purchase = await ShopLog.get_today_purchase_amount(
                    user_id=event.user_id, item_name=goods.name, connection=connection
                )
                if not goods.check_purchase_limit(amount=amount + today_purchase):
                    await buy.finish(f"该商品今日限购 {goods.purchase_limit} 个！")
            for group in goods.group:
                group = goods_manager.get_goods_group(group)
                if group and group.purchase_limit:
                    today_purchase = await ShopGroupLog.get_today_purchase_amount(
                        user_id=event.user_id,
                        group_name=group.name,
                        connection=connection,
                    )
                    if not group.check_purchase_limit(amount=amount + today_purchase):
                        await buy.finish(f"该类商品今日限购 {group.purchase_limit} 个")
            if user_prop.gold < price * amount:
                await buy.finish("金币不足！")
            user_prop.gold -= price * amount
            await user_prop.save(update_fields=["gold"], using_db=connection)
            await TransactionLog(
                user_id=event.user_id,
                gold_spent=price * amount,
                description=f"商店购买{amount}个{goods.name}",
            ).save(using_db=connection)
            await ShopLog(
                user_id=event.user_id, item_name=goods.name, amount=amount, price=price
            ).save(using_db=connection)
            for group in goods.group:
                await ShopGroupLog(
                    user_id=event.user_id, group_name=group, amount=amount
                ).save(using_db=connection)
        user, _ = await UserBag.get_or_create(
            user_id=event.user_id, item_name=goods.name, using_db=connection
        )
        user.amount += amount
        await user.save(update_fields=["amount"], using_db=connection)
    await buy.send(f"购买{amount}个{goods.name}成功！共花费{price * amount}个金币")


@my_bag.handle()
async def _(event: MessageEvent):
    user_bag = await UserBag.get_item_list(user_id=event.user_id)
    gold = await UserProperty.get_gold(user_id=event.user_id)
    user_status = await TransactionLog.get_gold_info(user_id=event.user_id)
    await my_bag.send(
        MessageSegment.image(
            await draw_bag(
                user_bag,
                (gold, user_status[0], user_status[1], user_status[2], user_status[3]),
            )
        ),
        at_sender=True,
    )


ret_to_msg = {
    UseStatus.NO_SUCH_ITEM_IN_BAG: "用户背包中无该物品",
    UseStatus.INSUFFICIENT_QUANTITY: "用户背包中数量不足，剩余可用{count}",
    UseStatus.USE_LIMIT: "物品今日剩余可用{count}，已达使用上限",
    UseStatus.GROUP_USE_LIMIT: "该类商品今日剩余可用{count}，已达使用上限",
    UseStatus.ITEM_DISABLED: "该物品已禁用",
    UseStatus.SUCCESS: "使用{name}x{count}成功",
    UseStatus.NO_SUCH_GOODS: "不存在这种道具呢",
    UseStatus.CANCELLED: "使用过程中...被中断了...（{reason}）",
    UseStatus.SINGLE_USE_LIMIT: "该道具单次只能使用{count}次！",
}


@use.handle()
async def _(bot: Bot, matcher: Matcher, event: MessageEvent, cmd: str = Startswith()):
    args = event.get_plaintext().removeprefix(cmd).split(" ")
    amount: int
    if len(args) == 2:
        args[1] = args[1].strip()
        if not args[1].isdigit():
            await use.finish("使用数量必须为正整数", at_sender=True)
        amount = int(args[1])
        if amount <= 0:
            await use.finish("使用数量必须为正整数", at_sender=True)
    else:
        amount = 1
    name = args[0].strip()
    if name.isdigit():
        name = int(name)
    status, kwargs = await goods_manager.use_goods(
        user_id=event.user_id,
        name=name,
        params=GoodsHandlerParams(
            goods_name=name,
            user_id=event.user_id,
            group_id=event.group_id if isinstance(event, GroupMessageEvent) else None,
            bot=bot,
            event=event,
            matcher=matcher,
            num=amount,
        ),
    )
    await use.send(ret_to_msg[status].format(**(kwargs or {})), at_sender=True)


@give_gold.handle()
async def _(event: GroupMessageEvent, args: Message = CommandArg()):
    user_list = []
    gold = args.extract_plain_text().strip()
    sign = 1
    if gold and gold[0] == "-":
        gold = gold[1:]
        sign = -1
    if not gold.isdigit():
        await give_gold.finish("金币数必须为整数")
    gold = int(gold) * sign
    for seg in event.message:
        if seg.type == "at" and seg.data["qq"] != "all":
            user_list.append(seg.data["qq"])
    for user in user_list:
        await UserProperty.modify_gold(
            user_id=user, gold_diff=gold, description="超级用户打钱了"
        )
    await give_gold.send("已成功赠与金币")


@modify.handle()
async def _(event: MessageEvent, cmd: str = Startswith()):
    args = event.get_plaintext().removeprefix(cmd).strip().split(" ")
    item = args[0].split(":")
    if len(item) != 2:
        await modify.finish("参数错误！")
    type_ = item[0]
    try:
        if type_ == "group" and goods_manager.get_goods_group(item[1]):
            await adjust_goods_group(item[1], " ".join(args[1:]))
        elif type_ == "goods" and goods_manager.get_goods(item[1]):
            await adjust_goods(item[1], " ".join(args[1:]))
        else:
            await modify.finish("商品/商品组不存在，请检查")
    except Exception as e:
        if e != FinishedException:
            await modify.send(f"调整异常：{e}")
    else:
        await modify.send(f"{item[1]} 调整成功！")
