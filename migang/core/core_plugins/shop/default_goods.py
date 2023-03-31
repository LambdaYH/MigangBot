import random
from pathlib import Path

from nonebot.adapters.onebot.v11 import (
    Bot,
    ActionFailed,
    MessageEvent,
    GroupMessageEvent,
)

from migang.core.models import UserProperty
from migang.core.decorator import CancelGoodsHandle, goods_register

ICON_PATH = Path(__file__).parent / "images" / "shop_icon"


@goods_register(
    name=("番茄薯片", "甜果果", "榴莲起司"),
    price=(200, 500, 1000),
    description=("好感度随机增加 1~7", "好感度随机增加 3~23", "好感度随机增加 0~61"),
    purchase_limit=(3, 2, 1),
    icon=(
        (ICON_PATH / "番茄薯片.png"),
        (ICON_PATH / "甜果果.png"),
        (ICON_PATH / "榴莲起司.png"),
    ),
    kwargs=({"low": 1, "high": 7}, {"low": 3, "high": 23}, {"low": 0, "high": 61}),
)
async def _(goods_name: str, user_id: int, bot: Bot, low: int, high: int):
    add_impression = random.uniform(low, high)
    await UserProperty.modify_impression(
        user_id=user_id, impression_diff=add_impression
    )
    return (
        random.choice(
            [
                f"哇！谢谢你的{goods_name}",
                f"谢谢！正想着要不要出门买{goods_name}呢~",
                f"好想吃{goods_name}啊，但是家里没有...咦？这是给我的吗！谢谢！！",
            ]
        )
        + f"\n[{list(bot.config.nickname)[0]}对您的好感度增加了{add_impression:.2f}"
    )


@goods_register(
    name="小袋星钻",
    price=20,
    description="可兑换为不定额（10~100）的金币哟~",
    purchase_limit=10,
    use_limit=10,
    single_use_limit=10,
    icon=ICON_PATH / "小袋星钻.png",
    kwargs={"low": 10, "high": 100},
)
async def _(goods_name: str, num: int, user_id: int, low: int, high: int):
    if num > 1:
        total_earn_gold = 0
        every_time_gold = []
        for _ in range(num):
            earn_gold = int(random.normalvariate(10, 32))
            while earn_gold < low or earn_gold > high:
                earn_gold = int(random.normalvariate(10, 32))
            total_earn_gold += earn_gold
            every_time_gold.append(str(earn_gold))
        await UserProperty.modify_gold(
            user_id=user_id,
            gold_diff=total_earn_gold,
            description=f"打开了{num}个{goods_name}",
        )
        return f"打开了{num}{goods_name}，碎钻与星钻交错散落。\n[您总共获得了{total_earn_gold}枚金币，每袋分别为{', '.join(every_time_gold)}枚]"
    earn_gold = int(random.normalvariate(10, 32))
    while earn_gold < low or earn_gold > high:
        earn_gold = int(random.normalvariate(10, 32))
    await UserProperty.modify_gold(
        user_id=user_id, gold_diff=earn_gold, description=f"打开了1个{goods_name}"
    )
    if earn_gold <= 40:
        msg = "碎钻散落"
    if earn_gold <= 60:
        msg = "碎钻密布，仿佛银河滴入了袋中"
    elif earn_gold <= 80:
        msg = "星钻寥若晨星，静静地躺在袋内"
    else:
        msg = "星钻撑得小袋子鼓鼓囊囊，灿若繁星"
    return f"轻轻打开了{goods_name}，{msg}。\n[您获得了{earn_gold}枚金币]"


@goods_register(
    name="床",
    price=800,
    description="躺上去享受8小时精致睡眠（需要Bot为管理员，使用后被禁言8h）",
    icon=ICON_PATH / "bed.png",
    use_limit=2,
    consumable=False,
)
async def _(bot: Bot, user_id: int, group_id: int, event: MessageEvent):
    try:
        await bot.set_group_ban(group_id=group_id, user_id=user_id, duration=8 * 3600)
    except ActionFailed:
        raise CancelGoodsHandle(f"{list(bot.config.nickname)[0]}无法使你睡眠哦~")
    return f"{event.sender.card or event.sender.nickname}进入了甜甜的梦乡，看起来要8h后才会起床了~"


@goods_register.before_handle(name="床")
async def _(event: MessageEvent):
    if not isinstance(event, GroupMessageEvent):
        raise CancelGoodsHandle("不许偷偷睡觉！")
