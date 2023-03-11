import random
import asyncio
from time import time
from io import BytesIO
from pathlib import Path
from enum import Enum, unique
from typing import List, Tuple

import anyio
from pil_utils import BuildImage
from PIL import ImageFont, ImageFilter

from migang.core import FONT_PATH
from migang.core.manager import goods_manager
from migang.core.utils.image import get_user_avatar

height = 50
side_width = 40
font_size = 30
icon_size = (40, 40)
row_gap = 10
column_gap = 10
IMAGE_PATH = Path(__file__).parent / "images"
bgs = list((IMAGE_PATH / "background").iterdir())
exchange_icon_path = IMAGE_PATH / "exchange_icon.png"
default_icon_path = IMAGE_PATH / "wenhao.png"
gold_ico_path = IMAGE_PATH / "gold_icon.png"
trade_bg_path = IMAGE_PATH / "trade_bg.png"

ttf_font = ImageFont.truetype(
    str(FONT_PATH / "HONORSansCN-Regular.ttf"), size=30, encoding="utf-8"
)


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


async def draw_trade_window(
    one_side: Tuple[int, TradingStatus],
    other_side: Tuple[int, TradingStatus],
) -> bytes:
    """_summary_

    Args:
        one_side (Tuple[int, int, List[Tuple[str, int]]]): 用户id，金币数，交易物（名字，数量）
        other_side (Tuple[int, int, List[Tuple[str, int]]]): 用户id，金币数，交易物（名字，数量）

    Returns:
        bytes: _description_
    """
    one_side_img, other_side_img = await asyncio.gather(
        *[
            anyio.to_thread.run_sync(
                draw,
                await get_user_avatar(one_side[0]),
                one_side[1].gold,
                one_side[1].items,
                0,
            ),
            anyio.to_thread.run_sync(
                draw,
                await get_user_avatar(other_side[0]),
                other_side[1].gold,
                other_side[1].items,
                1,
            ),
        ]
    )
    bg = BuildImage.open(trade_bg_path)
    exchange_icon = BuildImage.open(exchange_icon_path).resize((80, 80))
    total_width = (
        one_side_img.width + other_side_img.width + exchange_icon.width + 20 + 30
    )
    total_height = max(one_side_img.height, other_side_img.height) + 30
    if total_width > bg.width or total_height > bg.height:
        max_ratio = max(total_width / bg.width, total_height / bg.height)
        bg = bg.resize((int(max_ratio * bg.height), int(max_ratio * bg.width)))
    bg = bg.resize_canvas((total_width, total_height)).filter(ImageFilter.BLUR)
    bg.paste(one_side_img, (15, int((bg.height - one_side_img.height) / 2)), True)
    bg.paste(
        exchange_icon,
        (one_side_img.width + 15 + 10, int((bg.height - exchange_icon.height) / 2)),
        True,
    )
    bg.paste(
        other_side_img,
        (
            bg.width - other_side_img.width - 15,
            int((bg.height - other_side_img.height) / 2),
        ),
        True,
    )
    bg = bg.circle_corner(18)
    return bg.save_png()


def draw(
    avatar: bytes, gold: int, items: List[Tuple[str, int]], avatar_pos: int = 0
) -> BuildImage:
    """画

    Args:
        avatar (bytes): 头像
        gold (int): 金币
        items (List[Tuple[str, int]]): 物品 List[(物品名，数量)]
        avatar_pos (int, optional): 0为在左，1为在右. Defaults to 0.

    Returns:
        BuildImage: _description_
    """
    width = 200
    item_img = []
    for item in items:
        width = max(
            width,
            icon_size[0]
            + 5
            + int(ttf_font.getlength(item[0]))
            + side_width * 2
            + 5 * 4,
        )
    for item in items:
        item_name: str = item[0]
        amount: int = item[1]
        bg = BuildImage.new(
            "RGBA", size=(width, height), color=(255, 255, 255, 200)
        ).circle_corner(30)
        bg.draw_line(
            (bg.width - side_width, 5, bg.width - side_width, bg.height - 5),
            fill=(168, 168, 168, 230),
            width=2,
        )
        goods = goods_manager.get_goods(item_name)
        if goods and goods.icon:
            icon = goods.icon
        else:
            icon = default_icon_path
        bg.paste(
            BuildImage.open(icon).resize(icon_size).circle(),
            (5, 5),
            alpha=True,
        )
        bg.draw_text(
            (5 + icon_size[0] + 5, 5),
            text=item_name,
            fontname="HONOR Sans CN",
            fontsize=font_size,
        )
        bg.draw_text(
            (bg.width - side_width, 0, bg.width, bg.height),
            text=str(amount),
            fontname="HONOR Sans CN",
        )
        item_img.append(bg)

    gold_img_height = 50
    avatar_width = 50
    total_width = width + 15 * 2
    total_height = (
        height * len(item_img)
        + 20
        + gold_img_height
        + 10
        + row_gap * (len(item_img) - 1)
    )
    bg = BuildImage.open(random.choice(bgs)).convert("RGBA")
    if total_width > bg.width or total_height > bg.height:
        max_ratio = max(total_width / bg.width, total_height / bg.height)
        bg = bg.resize((int(max_ratio * bg.height), int(max_ratio * bg.width)))
    bg = bg.resize_canvas(
        (
            total_width,
            total_height,
        )
    ).circle_corner(18)
    avatar_bg = BuildImage.new(
        "RGBA", (avatar_width, gold_img_height), color=(255, 255, 255, 190)
    ).circle_corner(18)
    avatar_img = BuildImage.open(BytesIO(avatar)).resize((40, 40)).circle()
    avatar_bg.paste(avatar_img, (5, 5), True)

    gold_img = BuildImage.new(
        "RGBA",
        (bg.width - 30 - avatar_width - 5, gold_img_height),
        color=(255, 255, 255, 190),
    ).circle_corner(18)
    gold_icon = BuildImage.open(gold_ico_path).resize((40, 40))
    gold_img.paste(gold_icon, (5, int((gold_img.height - gold_icon.height) / 2)), True)
    gold_img.draw_text(
        (5 + 5, 5, gold_img.width - 5, gold_img.height - 5),
        text=str(gold),
        fontname="HONOR Sans CN",
    )

    if avatar_pos == 0:
        bg.paste(avatar_bg, (15, 10), True)
        bg.paste(gold_img, (15 + avatar_width + 5, 10), True)
    else:
        bg.paste(gold_img, (15, 10), True)
        bg.paste(avatar_bg, (15 + gold_img.width + 5, 10), True)
    height_start = gold_img_height + row_gap + 10
    for img in item_img:
        bg.paste(img, (15, height_start), True)
        height_start += height + row_gap
    return bg
