from pathlib import Path
from datetime import datetime

from pil_utils import BuildImage
from nonebot.params import Startswith
from nonebot.plugin import PluginMetadata
from nonebot import on_fullmatch, on_startswith
from tortoise.transactions import in_transaction
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment

from migang.core import ConfigItem, get_config
from migang.core.models.bank import DepositType
from migang.core.models import Bank, UserProperty

__plugin_meta__ = PluginMetadata(
    name="银行",
    description="银行",
    usage="""
指令：
    存金币 数额
    取金币 数额
    我的存款
""".strip(),
    extra={
        "unique_name": "migang_bank",
        "example": "rua",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_category__ = "基础功能"
__plugin_config__ = (
    ConfigItem(
        key="demand_deposit_rate",
        initial_value=12.06,
        default_value=12.06,
        description="活期存款利率，百分比/天",
    ),
)

deposit_coins = on_startswith("存金币", priority=True, block=True)
take_coins = on_startswith("取金币", priority=5, block=True)
my_deposit = on_fullmatch("我的存款", priority=5, block=True)

bg_path = Path(__file__).parent / "images" / "bg.jpg"


@deposit_coins.handle()
async def _(event: MessageEvent, cmd: str = Startswith()):
    amount = event.get_plaintext().removeprefix(cmd).strip()
    if not amount.isdigit():
        await deposit_coins(f"存入金额必须为正整数")
    amount = int(amount)
    async with in_transaction() as connection:
        now_gold = await UserProperty.get_gold(
            user_id=event.user_id, connection=connection
        )
        if now_gold < amount:
            await deposit_coins.finish(f"背包里的金币不够存哦~")
        await UserProperty.modify_gold(
            user_id=event.user_id,
            gold_diff=-amount,
            description="存入银行",
            connection=connection,
        )
        await Bank(user_id=event.user_id, amount=amount).save(
            update_fields=["amount"], using_db=connection
        )
    await deposit_coins.send(f"{amount}金币已经存放妥当了")


@take_coins.handle()
async def _(event: MessageEvent, cmd: str = Startswith()):
    amount = event.get_plaintext().removeprefix(cmd).strip()
    if not amount.isdigit():
        await deposit_coins(f"存入金额必须为正整数")
    amount = int(amount)
    ori_amount = amount
    async with in_transaction() as connection:
        total_demand_deposit = await Bank.get_total_demand_deposit(
            user_id=event.user_id, connection=connection
        )
        if total_demand_deposit < amount:
            await take_coins.finish(f"您未在这存放足够的金币哦~")
        # 先把晚存入的取出来
        rate = (await get_config("demand_deposit_rate")) / 100
        total_earned = 0
        now = datetime.utcnow()
        all_demand_deposit = (
            await Bank.filter(
                user_id=event.user_id, deposit_type=DepositType.demand_deposit
            )
            .order_by("-time")
            .all()
        )
        for demand_deposit in all_demand_deposit:
            if demand_deposit.amount >= amount:
                total_earned += int(
                    (now - demand_deposit.time.replace(tzinfo=None)).days
                    * rate
                    * amount
                )
                demand_deposit.amount -= amount
                await demand_deposit.save(update_fields=["amount"], using_db=connection)
                break
            else:
                total_earned += int(
                    (now - demand_deposit.time.replace(tzinfo=None)).days
                    * rate
                    * demand_deposit.amount
                )
                await demand_deposit.delete(using_db=connection)
                amount -= demand_deposit.amount
        await UserProperty.modify_gold(
            user_id=event.user_id,
            gold_diff=ori_amount + total_earned,
            description="从银行中取出",
            connection=connection,
        )
    await deposit_coins.send(f"{ori_amount}金币已经取出，收益{total_earned}金币")


@my_deposit.handle()
async def _(event: MessageEvent):
    total_demand_deposit = await Bank.get_total_demand_deposit(user_id=event.user_id)
    # 定期存款，懒得写
    # time_deposit = await Bank.filter(
    #     user_id=event.user_id, deposit_type=DepositType.time_deposit
    # ).all()
    bg_img = BuildImage.open(bg_path)
    demand_img = BuildImage.new("RGBA", (600, 200), (255, 255, 255, 200)).circle_corner(
        r=18
    )
    demand_img.draw_text(
        xy=(150, 5), text="活", fontsize=50, max_fontsize=50, fontname="HONOR Sans CN"
    )
    demand_img.draw_text(
        xy=(demand_img.width - 205, 5),
        text="期",
        fontsize=50,
        max_fontsize=50,
        fontname="HONOR Sans CN",
    )
    demand_img.draw_line(
        xy=(5, 80, demand_img.width - 5, 80), fill=(255, 255, 255, 230), width=3
    )
    demand_img.draw_text(
        xy=(5, 85, demand_img.width - 5, demand_img.height - 5),
        text=str(total_demand_deposit),
        fontname="HONOR Sans CN",
    )
    bg_img = bg_img.resize_canvas(size=(demand_img.width + 30, demand_img.height + 30))
    bg_img.paste(img=demand_img, pos=(15, 15), alpha=True)
    await my_deposit.send(MessageSegment.image(bg_img.save_png()))
