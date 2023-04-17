import bisect
import random
import secrets
from io import BytesIO
from typing import Tuple
from decimal import Decimal
from datetime import datetime

import anyio
from nonebot.log import logger
from pil_utils import BuildImage
from tortoise.transactions import in_transaction

from migang.core.decorator import sign_in_effect
from migang.core.utils.image import get_user_avatar
from migang.core.models import SignIn, UserProperty, TransactionLog

from . import effects
from .const import (
    SIGN_BORDER_PATH,
    SIGN_RESOURCE_PATH,
    SIGN_BACKGROUND_PATH,
    lik2level,
    lik2relation,
    level2attitude,
)

TIMEDELTA = datetime.now() - datetime.utcnow()


async def handle_sign_in(user_id: int, user_name: str, bot_name: str):
    async with in_transaction() as connection:
        user = await SignIn.filter(user_id=user_id).using_db(connection).first()
        user_prop = (
            await UserProperty.filter(user_id=user_id).using_db(connection).first()
        )
        impression_diff: str
        if user and (user.time + TIMEDELTA).date() == datetime.now().date():
            impression_diff = f"{user.impression_diff:.2f}"
        else:
            if not user:
                user = SignIn(user_id=user_id)
            if not user_prop:
                user_prop = UserProperty(user_id=user_id)
            # 签到基础作用
            user.gold_diff = random.randint(1, 100)
            user.impression_diff = (secrets.randbelow(99) + 1) / 10
            pre_impression_diff = user.impression_diff
            user.signin_count += 1
            user_prop.impression += Decimal(user.impression_diff)
            user_prop.gold += user.gold_diff
            # 触发上一次效果
            for i, next_effect in enumerate(user.next_effect):
                if effect := sign_in_effect.get_effect_by_name(name=next_effect):
                    if effect.has_next_effect():
                        try:
                            await effect.next_effect(
                                user_id=user_id,
                                user_sign_in=user,
                                user_prop=user_prop,
                                **user.next_effect_params[i],
                            )
                        except Exception as e:
                            logger.warning(f"执行 {effect.name} 的下一次触发签到效果发生异常：{e}")
                    else:
                        logger.warning(f"签到效果 {effect.name} 不存在下一次签到的效果，但被触发了")
            # 触发随机效果
            effect = sign_in_effect.random_effect()
            try:
                effect_ret = await effect(
                    user_id=user_id, user_sign_in=user, user_prop=user_prop
                )
                # 记录下一次的
                if isinstance(effect_ret, str):
                    user.windfall = effect_ret
                    if effect.has_next_effect():
                        user.next_effect = [effect.name]
                        user.next_effect_params = [{}]
                    else:
                        user.next_effect = user.next_effect_params = []
                else:
                    user.windfall, params = effect_ret
                    if effect.has_next_effect():
                        user.next_effect = [effect.name]
                        if params is None:
                            params = [{}]
                        user.next_effect_params = [params]
                    else:
                        user.next_effect = user.next_effect_params = []
            except Exception as e:
                logger.warning(f"执行 {effect.name} 的本次签到效果发生异常：{e}")
            await TransactionLog(
                user_id=user_id, gold_earned=user.gold_diff, description="签到"
            ).save(using_db=connection)
            post_impression_diff = user.impression_diff
            magnification = f"{post_impression_diff / pre_impression_diff:g}"
            magnification = (
                f"{float(magnification):.1f}" if "." in magnification else magnification
            )
            if magnification != "1":
                impression_diff = (
                    f"{pre_impression_diff} [color=red]x {magnification}[/color]"
                )
            else:
                impression_diff = f"{pre_impression_diff}"
            await user.save(using_db=connection)
            await user_prop.save(using_db=connection)
    avatar = await get_user_avatar(user_id)
    return await anyio.to_thread.run_sync(
        draw,
        bot_name,
        avatar,
        user_id,
        user_name,
        user.signin_count,
        user.gold_diff,
        impression_diff,
        user.windfall,
        user_prop.impression,
        user.time + TIMEDELTA,
    )


def get_level_and_next_impression(impression: float) -> Tuple[int, int, int]:
    """_summary_

    Args:
        impression (float): _description_

    Returns:
        Tuple[int, int, int]: 等级，下一等级所需好感度，上一等级所需好感度
    """
    if impression == 0:
        return lik2level[0], 12, impression
    lik2level_list = list(lik2level)
    idx = bisect.bisect_left(lik2level_list, impression)
    if idx == len(lik2level):
        return "∞", 1, 0
    return (
        lik2level[lik2level_list[idx - 1]],
        lik2level_list[idx],
        lik2level_list[idx - 1],
    )


def draw(
    bot_name: str,
    avatar: bytes,
    user_id: int,
    user_name: str,
    count: int,
    gold_diff: int,
    impression_diff: str,
    windfall: str,
    impression: float,
    time: datetime,
):
    avatar_img = BuildImage.open(BytesIO(avatar)).resize((102, 102)).circle()
    avatar_border = (
        BuildImage.open(SIGN_BORDER_PATH / "ava_border_01.png")
        .convert("RGBA")
        .resize((140, 140))
    )

    level, next_impression, previous_impression = get_level_and_next_impression(
        impression
    )
    interpolation = next_impression - impression
    if level == "∞":
        level = "8"
        next_impression = impression
        interpolation = 0

    bar_bk = (
        BuildImage.open(SIGN_RESOURCE_PATH / "bar_white.png")
        .convert("RGBA")
        .resize((220, 20))
    )
    ratio = 1 - (next_impression - impression) / (next_impression - previous_impression)
    bar = BuildImage.open(SIGN_RESOURCE_PATH / "bar.png").resize((220, 20))
    bar_bk.paste(
        bar,
        (int(bar.width * ratio) - bar.width, 0),
        alpha=True,
    )
    gift_border = BuildImage.open(SIGN_BORDER_PATH / "gift_border_02.png").resize(
        (270, 100)
    )
    gift_border.draw_text(
        (0, 0, gift_border.width, gift_border.height),
        windfall,
        lines_align="center",
        fontname="Yozai",
    )
    bk = (
        BuildImage.open(random.choice(list(SIGN_BACKGROUND_PATH.iterdir())))
        .convert("RGBA")
        .resize((876, 424))
    )
    sub_bk = BuildImage.new("RGBA", (876, 274), (255, 255, 255, 190))
    sub_bk.paste(avatar_border, (25, 80), True)
    sub_bk.paste(avatar_img, (45, 99), True)
    sub_bk.draw_line((200, 70, 200, 250), width=2, fill=(0, 0, 0))

    user_id = str(user_id).rjust(12, "0")
    user_id = user_id[:4] + " " + user_id[4:8] + " " + user_id[8:]
    sub_bk.paste(gift_border, (570, 140), True)
    bk.draw_text(
        (30, 15),
        text=user_name,
        fontname="Yozai",
        fontsize=50,
        max_fontsize=50,
        fill=(255, 255, 255),
    )
    bk.draw_text(
        (30, 85),
        text=f"UID: {user_id}",
        fontname="Yozai",
        fontsize=30,
        max_fontsize=50,
        fill=(255, 255, 255),
    )
    bk.paste(sub_bk, (0, 150), alpha=True)
    bk.draw_bbcode_text(
        xy=(30, 157),
        text=f"Accumulative check-in for [size=40][color=#D34021]{count}[/color][/size] days",
        fontname="Yozai",
        fontsize=25,
    )
    bk.paste(bar_bk, (225, 275), True)
    bk.draw_text(
        (220, 370),
        text=f"时间：{time.strftime('%Y-%m-%d %a %H:%M:%S')}",
        fontname="Yozai",
        fontsize=20,
    )
    bk.draw_text(
        (220, 240),
        text="当前",
        fontname="Yozai",
        fontsize=20,
    )
    bk.draw_text(
        (262, 234),
        text=f"好感度：{impression:.2f}",
        fontname="Yozai",
        fontsize=30,
    )
    bk.draw_text(
        (220, 305),
        text=f"· 好感度等级：{level} [{lik2relation[level]}]",
        fontname="Yozai",
        fontsize=15,
    )
    bk.draw_text(
        (220, 325),
        text=f"· {bot_name}对你的态度：{level2attitude[level]}",
        fontname="Yozai",
        fontsize=15,
    )
    bk.draw_text(
        (220, 345),
        text=f"· 距离升级还差 {interpolation:.2f} 好感度",
        fontname="Yozai",
        fontsize=15,
    )
    bk.draw_text(
        (550, 180),
        text="今日签到",
        fontsize=30,
        fontname="Yozai",
    )
    bk.draw_text(
        (580, 220),
        text=f"好感度 + {impression_diff}",
        fontsize=20,
        fontname="Yozai",
    )
    bk.draw_text(
        (580, 245),
        text=f"金币 + {gold_diff}",
        fontsize=20,
        fontname="Yozai",
    )
    # 水印
    bk.draw_text(
        (15, 400),
        text=f"{bot_name}@{datetime.now().year}",
        fontsize=15,
        fontname="Yozai",
        fill=(155, 155, 155),
    )
    return bk.save_png()
