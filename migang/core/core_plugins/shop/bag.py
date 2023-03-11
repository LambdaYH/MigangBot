import math
import random
from pathlib import Path
from typing import List, Tuple

from PIL import ImageFont
from pil_utils import BuildImage

from migang.core import FONT_PATH
from migang.core.models import UserBag
from migang.core.manager import goods_manager

height = 50
side_width = 40
font_size = 30
icon_size = (40, 40)
row_gap = 10
column_gap = 10
IMAGE_PATH = Path(__file__).parent / "images"
bag_bk = list((IMAGE_PATH / "bag_bk").iterdir())
default_icon = IMAGE_PATH / "wenhao.png"

ttf_font = ImageFont.truetype(
    str(FONT_PATH / "HONORSansCN-Regular.ttf"), size=30, encoding="utf-8"
)


def draw_bag(
    user_bag: List[UserBag], gold_status: Tuple[int, int, int, int, int]
) -> bytes:
    item_img: List[BuildImage] = []
    width = 200
    for item in user_bag:
        width = max(
            width,
            icon_size[0]
            + 5
            + int(ttf_font.getlength(item.item_name))
            + side_width * 2
            + 5 * 4,
        )
    for i, item in enumerate(user_bag):
        bk = BuildImage.new(
            "RGBA", size=(width, height), color=(255, 255, 255, 200)
        ).circle_corner(30)
        bk.draw_line(
            (side_width, 5, side_width, bk.height - 5),
            fill=(168, 168, 168, 230),
            width=2,
        )
        bk.draw_line(
            (bk.width - side_width, 5, bk.width - side_width, bk.height - 5),
            fill=(168, 168, 168, 230),
            width=2,
        )
        goods = goods_manager.get_goods(item.item_name)
        if goods and goods.passive:
            bk.draw_text(
                (5, 0, side_width, bk.height),
                "被\n动",
                fontname="HONOR Sans CN",
            )
        else:
            bk.draw_text(
                (5, 0, side_width, bk.height),
                str(i + 1),
                fontname="HONOR Sans CN",
            )
        if goods and goods.icon:
            icon = goods.icon
        else:
            icon = default_icon
        bk.paste(
            BuildImage.open(icon).resize(icon_size).circle(),
            (side_width + 5, 5),
            alpha=True,
        )
        bk.draw_text(
            (side_width + 5 + icon_size[0] + 5, 5),
            text=item.item_name,
            fontname="HONOR Sans CN",
            fontsize=font_size,
        )
        bk.draw_text(
            (bk.width - side_width, 0, bk.width, bk.height),
            text=str(item.amount),
            fontname="HONOR Sans CN",
        )
        item_img.append(bk)

    bk = BuildImage.open(random.choice(bag_bk)).convert("RGBA")
    my_gold_height = 100
    my_gold = BuildImage.new(
        "RGBA", (bk.width - 40, my_gold_height), color=(255, 255, 255, 190)
    ).circle_corner(18)
    each_width = my_gold.width // 5
    for i, text in enumerate(["我的金币", "今日获得", "今日消耗", "总获得", "总消耗"]):
        my_gold.draw_text(
            (each_width * i, 0, each_width * (i + 1), my_gold_height // 3),
            text=text,
            fontname="HONOR Sans CN",
        )
    for i in range(4):
        my_gold.draw_line(
            (each_width * (i + 1), 8, each_width * (i + 1), my_gold_height - 8),
            width=2,
            fill=(168, 168, 168, 230),
        )
    for i, gold in enumerate(gold_status):
        my_gold.draw_text(
            (
                each_width * i + 5,
                my_gold_height // 3,
                each_width * (i + 1) - 5,
                my_gold_height - 5,
            ),
            text=str(gold),
            fontname="HONOR Sans CN",
        )
    bk.paste(my_gold, (20, 10), True)
    height_start = my_gold_height + 20
    height_end = 30
    row_limit = math.floor(
        (bk.height - height_start - height_end + row_gap) / (height + row_gap)
    )
    level_width: List[int] = [20] * row_limit
    for i, img in enumerate(item_img):
        bk.paste(
            img,
            (
                level_width[i % row_limit],
                height_start + (i % row_limit) * (height + row_gap),
            ),
            alpha=True,
        )
        level_width[i % row_limit] += img.width + column_gap
    return bk.save_png()
