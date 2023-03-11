import math
import random
from io import BytesIO
from pathlib import Path
from typing import List, Tuple

from pil_utils import BuildImage
from PIL import ImageFont, ImageFilter

from migang.core import FONT_PATH
from migang.core.manager import goods_manager

IMAGE_PATH = Path(__file__).parent / "images"
default_icon = IMAGE_PATH / "wenhao.png"
sticky_notes = list((IMAGE_PATH / "sticky_notes").iterdir())
nikki_img = BuildImage.open(IMAGE_PATH / "nikki_in_hutong.png")

goods_img_gap = 10
width_for_sticky_note = 120
line_height = 40
icon_size = (72, 72)


def split_text(
    text: str,
    line_width: Tuple[int, ...] = (280, 460),
    line_num: Tuple[int, ...] = (3, None),
    font: ImageFont = ImageFont.truetype(str(FONT_PATH / "FZSJ-QINGCRJ.ttf")),
) -> List[str]:
    """按照字体所显示出来的长度分成不同长度的列组

    Args:
        text (str): 文字
        line_width (Tuple[int, ...], optional): 各分组占的宽度. Defaults to (280, 460).
        line_num (Tuple[int, ...], optional): 各分组长度，若None则直接到结尾. Defaults to (3, None).
        font (ImageFont, optional): 显示所用的字体，用来计算宽度. Defaults to ImageFont.truetype(str(FONT_PATH / "FZSJ-QINGCRJ.ttf")).

    Returns:
        List[str]: rua
    """
    ret: List[str] = []
    for idx, num in enumerate(line_width):
        start = 0
        for i in range(math.ceil(font.getlength(text) / num)):
            if i == line_num[idx]:
                break
            lo = start
            hi = len(text)
            mid: int
            while lo < hi:
                mid = int(lo + (hi - lo) / 2)
                wcs_w = font.getlength(text[start:mid])
                if wcs_w >= num:
                    hi = mid
                else:
                    lo = mid + 1
            ret.append(text[start:hi])
            start = hi
        text = text[start:]
    return ret


def draw_shop() -> BytesIO:
    all_goods = goods_manager.get_all_goods_on_shelves()
    goods_imgs: List[BuildImage] = []
    height = 200
    # 画每个商品
    for goods in all_goods:
        lines = split_text(text=goods.description)
        goods_bk = BuildImage.open(IMAGE_PATH / "shop_item_bk.png")
        bk = BuildImage.open(IMAGE_PATH / "纸.png").resize(
            (800, max(len(lines) * 40, goods_bk.height + 17))
        )
        bk = BuildImage.new(
            "RGBA",
            size=(bk.width + width_for_sticky_note, bk.height + 10),
            color=(255, 255, 255, 0),
        ).paste(bk, (0, 10))
        # 画说明
        last_height = 10
        for i, line in enumerate(lines):
            start_x = goods_bk.width + 10
            if i >= 3:
                start_x = 30
            bk.draw_bbcode_text(
                text=line,
                xy=(start_x, last_height + 7),
                fontname="FZSJ-QINGCRJ",
                fontsize=16,
            )
            last_height += line_height
        last_height = 10
        for _ in range(max(3, len(lines))):
            bk.draw_line(
                xy=(
                    20,
                    last_height + 30,
                    bk.width - 20 - width_for_sticky_note,
                    last_height + 30,
                ),
                fill="black",
                width=2,
            )
            last_height += line_height
        # 画logo
        icon = (
            BuildImage.open(goods.icon).resize(icon_size).circle()
            if goods.icon
            else BuildImage.open(default_icon).resize(icon_size).circle()
        )
        goods_bk.paste(icon, (186, 7), alpha=True)
        # 画名字
        goods_bk.draw_bbcode_text(
            (2, 11, 172, 37), text=goods.name, fontname="Yozai", fontsize=20
        )
        # 画价格
        goods_bk.draw_bbcode_text(
            (5, 45), text="价格", fontname="CJGaoDeGuo-MH", fontsize=30
        )
        if goods.discount == 1:
            goods_bk.draw_bbcode_text(
                (42, 42, 170, 120),
                text=str(goods.price),
                fontname="DS-Digital",
                fontsize=90,
                max_fontsize=90,
            )
        else:
            goods_bk.draw_bbcode_text(
                (5, 90, 50, 120),
                text=str(goods.price),
                fontname="DS-Digital",
                fontsize=25,
            )
            goods_bk.draw_line((7, 90, 46, 117), fill=(255, 0, 0), width=3)
            goods_bk.draw_bbcode_text(
                (42, 42, 170, 120),
                text=str(int(goods.price * goods.discount)),
                fontname="DS-Digital",
                fontsize=90,
                max_fontsize=90,
                fill=(255, 0, 0),
            )
            goods_bk.draw_bbcode_text(
                (175, 85),
                text=f"-{100 - int(goods.discount * 100)}%",
                fontname="FZSJ-QINGCRJ",
                fontsize=25,
            )
        # 画日限制
        if goods.purchase_limit is not None:
            limit_img = BuildImage.open(random.choice(sticky_notes))
            limit_img = limit_img.resize(
                (int(120 * (limit_img.width / limit_img.height)), 120)
            )
            limit_img.draw_bbcode_text(
                (0, 20, limit_img.width, limit_img.height),
                text=str(goods.purchase_limit),
                fontname="EASTER CHALK",
                fontsize=26,
                fill=(255, 0, 0),
            )
            bk.paste(
                limit_img,
                (
                    bk.width - 120 - random.randint(2, 15),
                    (bk.height - limit_img.height) // 2,
                ),
                alpha=True,
            )
        bk.paste(goods_bk, (0, 0), alpha=True)
        height += bk.height
        goods_imgs.append(bk)

    height += (len(goods_imgs) - 1) * goods_img_gap
    bk = BuildImage.new(
        "RGBA",
        (
            1206,
            max(nikki_img.height, height),
        ),
        color=(255, 255, 255),
    )
    bk.paste(nikki_img, (0, int((bk.height - nikki_img.height) / 2)))
    # 画黑黑的长方体
    bk.draw_polygon(
        [
            (nikki_img.width, 130),
            (nikki_img.width + 40, 130),
            (nikki_img.width + 40, bk.height - 20),
            (nikki_img.width, bk.height - 20),
        ],
        fill=(59, 49, 49),
    )
    # 侧面
    bk.draw_polygon(
        [
            (nikki_img.width + 40, 130),
            (nikki_img.width + 50, 140),
            (nikki_img.width + 50, bk.height - 10),
            (nikki_img.width + 40, bk.height - 20),
        ],
        fill=(47, 39, 39),
    )
    # 底部小方
    bk.draw_polygon(
        [
            (nikki_img.width, bk.height - 20),
            (nikki_img.width + 40, bk.height - 20),
            (nikki_img.width + 50, bk.height - 10),
            (nikki_img.width + 10, bk.height - 10),
        ],
        fill=(35, 23, 23),
    )
    # 把商品画上去
    last_height = 150
    for i, img in enumerate(goods_imgs):
        bk.paste(img, (nikki_img.width + 51, last_height), alpha=True)
        bk.draw_text(
            (nikki_img.width + 17, last_height + 30),
            text=str(i + 1),
            fontname="EASTER CHALK",
            fontsize=25,
            fill=(255, 255, 255, 178),
        )
        last_height += img.height + goods_img_gap
    # 画阴影
    start_alpha = 100
    shadow = BuildImage.new("RGBA", (80, bk.height - 7 - 140), color=(0, 0, 0, 0))
    step = math.ceil(start_alpha / shadow.width)
    for y in range(shadow.height):
        for x in range(shadow.width):
            if y < 3 / shadow.width * x or y > 3 / shadow.width * x + shadow.height - 3:
                continue
            shadow.draw_point((x, y), fill=(0, 0, 0, max(start_alpha - step * x, 0)))
    shadow = shadow.filter(ImageFilter.BLUR)
    bk.paste(shadow, (nikki_img.width + 50, 140), alpha=True)
    # 写个大字
    bk.draw_text(
        (395, 30),
        text="商   品   列   表",
        fontname="DFBuDingW12-GB",
        fontsize=60,
        max_fontsize=60,
    )
    return bk.save_png()
