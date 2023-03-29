import random
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Tuple, Union

import ujson as json
from pil_utils import BuildImage
from nonebot.utils import run_sync

from migang.core import DATA_PATH

ALC_PATH = DATA_PATH / "migang_genshin" / "almanac"
ALC_PATH.mkdir(exist_ok=True, parents=True)

CONFIG_PATH = Path(__file__).parent / "res" / "config.json"

BACKGROUND_PATH = Path(__file__).parent / "res" / "back.png"

chinese = {
    "0": "十",
    "1": "一",
    "2": "二",
    "3": "三",
    "4": "四",
    "5": "五",
    "6": "六",
    "7": "七",
    "8": "八",
    "9": "九",
}


@dataclass
class Fortune:
    title: str
    desc: str


def random_fortune() -> Tuple[List[Fortune], List[Fortune]]:
    """
    说明:
        随机运势
    """
    data = json.load(CONFIG_PATH.open("r", encoding="utf8"))
    fortune_data = {}
    good_fortune = []
    bad_fortune = []
    while len(fortune_data) < 6:
        r = random.choice(list(data.keys()))
        if r not in fortune_data:
            fortune_data[r] = data[r]
    for i, k in enumerate(fortune_data):
        if i < 3:
            good_fortune.append(
                Fortune(title=k, desc=random.choice(fortune_data[k]["buff"]))
            )
        else:
            bad_fortune.append(
                Fortune(title=k, desc=random.choice(fortune_data[k]["debuff"]))
            )
    return good_fortune, bad_fortune


def int2cn(v: Union[str, int]):
    """
    说明:
        数字转中文
    参数:
        :param v: str
    """
    return "".join([chinese[x] for x in str(v)])


@run_sync
def build_alc_image() -> Path:
    """
    说明:
        构造今日运势图片
    """
    path = ALC_PATH / f"{datetime.now().date()}.png"
    if path.exists():
        return path
    good_fortune, bad_fortune = random_fortune()
    background = BuildImage.open(BACKGROUND_PATH)
    now = datetime.now()
    background.draw_text(
        (78, 145), str(now.year), fill="#8d7650ff", fontsize=30, fontname="HYWenHei"
    )
    month = str(now.month)
    month_w = 358
    if now.month < 10:
        month_w = 373
    elif now.month != 10:
        month = "0" + month[-1]
    background.draw_text(
        (month_w, 145),
        f"{int2cn(month)}月",
        fill="#8d7650ff",
        fontsize=30,
        fontname="HYWenHei",
    )
    day = str(now.day)
    if now.day > 10 and day[-1] != "0":
        day = day[0] + "0" + day[-1]
    day_str = f"{int2cn(day)}日"
    day_w = 193
    if (n := len(day_str)) == 3:
        day_w = 207
    elif n == 2:
        day_w = 228
    background.draw_text(
        (day_w, 145),
        f"{int2cn(day)}日",
        fill="#f7f8f2ff",
        fontsize=35,
        fontname="HYWenHei",
    )
    fortune_h = 230
    for fortune in good_fortune:
        background.draw_text(
            (150, fortune_h),
            fortune.title,
            fill="#756141ff",
            fontsize=25,
            fontname="HYWenHei",
        )
        background.draw_text(
            (150, fortune_h + 28),
            fortune.desc,
            fill="#b5b3acff",
            fontsize=19,
            fontname="HYWenHei",
        )
        fortune_h += 55
    fortune_h += 4
    for fortune in bad_fortune:
        background.draw_text(
            (150, fortune_h),
            fortune.title,
            fill="#756141ff",
            fontsize=25,
            fontname="HYWenHei",
        )
        background.draw_text(
            (150, fortune_h + 28),
            fortune.desc,
            fill="#b5b3acff",
            fontsize=19,
            fontname="HYWenHei",
        )
        fortune_h += 55
    with open(path, "wb") as f:
        f.write(background.save_png().getvalue())
    return path
