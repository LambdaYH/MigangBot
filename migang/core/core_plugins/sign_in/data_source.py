import random
import secrets
import anyio

import bisect
from io import BytesIO
from datetime import datetime
from decimal import Decimal
from typing import Tuple

from nonebot.log import logger
from nonebot import get_driver
from nonebot_plugin_imageutils import BuildImage, text2image
from nonebot_plugin_imageutils.fonts import add_font
from tortoise.transactions import in_transaction

from migang.core.models import UserProperty, SignIn
from migang.core.path import FONT_PATH
from migang.core.decorator import sign_in_effect
from migang.core.utils.image import get_user_avatar

from .const import (
    SIGN_BACKGROUND_PATH,
    SIGN_BORDER_PATH,
    SIGN_RESOURCE_PATH,
    level2attitude,
    lik2level,
    lik2relation,
)
from .effects import *


@get_driver().on_startup
async def _():
    await add_font("yz.ttf", FONT_PATH / "yz.ttf")


async def handle_sign_in(user_id: int, user_name: str, bot_name: str):
    user_next_effect, user_next_effect_params = None, None
    async with in_transaction() as connection:
        user = await SignIn.filter(user_id=user_id).using_db(connection).first()
        user_prop = (
            await UserProperty.filter(user_id=user_id).using_db(connection).first()
        )
        if user and user.time.date() == datetime.now().date():
            pass
        else:
            if not user:
                user = SignIn(user_id=user_id)
            if not user_prop:
                user_prop = UserProperty(user_id=user_id)
            # 签到基础作用
            user.gold_diff = random.randint(1, 100)
            user.impression_diff = (secrets.randbelow(99) + 1) / 10
            user.signin_count += 1
            user_prop.impression += Decimal(user.impression_diff)
            user_prop.gold += user.gold_diff
            # 触发上一次效果
            if user.next_effect is not None:
                if effect := sign_in_effect.get_effect_by_name(name=user.next_effect):
                    if effect.has_next_effect():
                        try:
                            await effect.next_effect(
                                user_id=user_id,
                                user_sign_in=user,
                                user_prop=user_prop,
                                **user.next_effect_params,
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
            except Exception as e:
                logger.warning(f"执行 {effect.name} 的本次签到效果发生异常：{e}")
            # 记录下一次的
            if isinstance(effect_ret, str):
                user.windfall = effect_ret
                if effect.has_next_effect():
                    user.next_effect = effect.name
                    user.next_effect_params = {}
                else:
                    user.next_effect = user.next_effect_params = None
            else:
                user.windfall, params = effect_ret
                if effect.has_next_effect():
                    user.next_effect = effect.name
                    if params is None:
                        params = {}
                    user.next_effect_params = params
                else:
                    user.next_effect = user.next_effect_params = None
            await user.save(using_db=connection)
            await user_prop.save(using_db=connection)

    avatar = await get_user_avatar(user_id)
    return await anyio.run_sync_in_worker_thread(
        draw,
        bot_name,
        avatar,
        user_id,
        user_name,
        user.signin_count,
        user.gold_diff,
        user.impression_diff,
        user.windfall,
        user_prop.impression,
    )


def get_level_and_next_impression(impression: float) -> Tuple[int, int, int]:
    """_summary_

    Args:
        impression (float): _description_

    Returns:
        Tuple[int, int, int]: 等级，下一等级所需好感度，上一等级所需好感度
    """
    if impression == 0:
        return lik2level[10], 10, 0
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
    impression_diff: float,
    windfall: str,
    impression: float,
):
    avatar_img = BuildImage.open(BytesIO(avatar)).resize((102, 102))
    avatar_img = avatar_img.circle()
    avatar_bk = BuildImage.new("RGBA", (140, 140), (255, 255, 255, 0))
    avatar_borader = BuildImage.open(SIGN_BORDER_PATH / "ava_border_01.png").resize(
        (140, 140)
    )
    avatar_bk.paste(
        avatar_img,
        pos=(
            int((avatar_bk.width - avatar_img.width) / 2),
            int((avatar_bk.height - avatar_img.height) / 2),
        ),
    )
    avatar_bk.paste(
        avatar_borader,
        alpha=True,
        pos=(
            int((avatar_bk.width - avatar_bk.width) / 2),
            int((avatar_bk.height - avatar_bk.height) / 2),
        ),
    )

    level, next_impression, previous_impression = get_level_and_next_impression(
        impression
    )
    interpolation = next_impression - impression
    if level == "∞":
        level = "8"
        next_impression = impression
        interpolation = 0

    bar_bk = BuildImage.open(SIGN_RESOURCE_PATH / "bar_white.png").resize((220, 20))
    bar = BuildImage.open(SIGN_RESOURCE_PATH / "bar.png").resize((220, 20))
    bar_bk.paste(
        bar,
        (
            -int(
                220
                * (
                    (next_impression - impression)
                    / (next_impression - previous_impression)
                )
            ),
            0,
        ),
        alpha=True,
    )
    gift_border = BuildImage.open(SIGN_BORDER_PATH / "gift_border_02.png").resize(
        (270, 100)
    )
    gift_border.draw_text(
        (0, 0, gift_border.width, gift_border.height),
        windfall,
        lines_align="center",
        fontname="yz.ttf",
    )
    bk = BuildImage.open(random.choice(list(SIGN_BACKGROUND_PATH.iterdir()))).resize(
        (876, 424)
    )
    sub_bk = BuildImage.new("RGBA", (876, 274), (255, 255, 255, 190))
    sub_bk.paste(avatar_bk, (25, 80), True)
    sub_bk.draw_line((200, 70, 200, 250), width=2, fill=(0, 0, 0))

    user_id = str(user_id).rjust(12, "0")
    user_id = user_id[:4] + " " + user_id[4:8] + " " + user_id[8:]
    sign_day_img = text2image(
        text=f"{count}",
        bg_color=(255, 255, 255, 0),
        fontsize=40,
        fontname="yz.ttf",
        fill=(211, 64, 33),
        padding=(0, 0),
    )
    current_date = datetime.now()
    sub_bk.paste(gift_border, (570, 140), True)
    bk.draw_text(
        (30, 15),
        text=user_name,
        fontname="yz.ttf",
        fontsize=50,
        max_fontsize=50,
        fill=(255, 255, 255),
    )
    bk.draw_text(
        (30, 85),
        text=f"UID: {user_id}",
        fontname="yz.ttf",
        fontsize=30,
        max_fontsize=50,
        fill=(255, 255, 255),
    )
    bk.paste(sub_bk, (0, 150), alpha=True)
    bk.draw_text((30, 167), "Accumulative check-in for", fontname="yz.ttf", fontsize=25)
    from PIL import ImageFont

    ttffont = ImageFont.truetype(font=str(FONT_PATH / "yz.ttf"), size=25)
    _x = ttffont.getsize("Accumulative check-in for")[0] + 45 + sign_day_img.width
    bk.paste(sign_day_img, (346, 158), True)
    bk.draw_text((_x, 167), "days", fontsize=25, fontname="yz.ttf")
    bk.paste(bar_bk, (225, 275), True)
    bk.draw_text(
        (220, 370),
        text=f"时间：{current_date.strftime('%Y-%m-%d %a %H:%M:%S')}",
        fontname="yz.ttf",
        fontsize=20,
    )
    bk.draw_text(
        (220, 240),
        text="当前",
        fontname="yz.ttf",
        fontsize=20,
    )
    bk.draw_text(
        (262, 234),
        text=f"好感度：{impression:.2f}",
        fontname="yz.ttf",
        fontsize=30,
    )
    bk.draw_text(
        (220, 305),
        text=f"· 好感度等级：{level} [{lik2relation[level]}]",
        fontname="yz.ttf",
        fontsize=15,
    )
    bk.draw_text(
        (220, 325),
        text=f"· {bot_name}对你的态度：{level2attitude[level]}",
        fontname="yz.ttf",
        fontsize=15,
    )
    bk.draw_text(
        (220, 345),
        text=f"· 距离升级还差 {interpolation:.2f} 好感度",
        fontname="yz.ttf",
        fontsize=15,
    )
    bk.draw_text(
        (550, 180),
        text="今日签到",
        fontsize=30,
        fontname="yz.ttf",
    )
    bk.draw_text(
        (580, 220),
        text=f"好感度 + {impression_diff:.2f}",
        fontsize=20,
        fontname="yz.ttf",
    )
    bk.draw_text(
        (580, 245),
        text=f"星钻 + {gold_diff}",
        fontsize=20,
        fontname="yz.ttf",
    )
    # 水印
    bk.draw_text(
        (15, 400),
        text=f"{bot_name}@{datetime.now().year}",
        fontsize=15,
        fontname="yz.ttf",
        fill=(155, 155, 155),
    )
    return bk.save_png()
