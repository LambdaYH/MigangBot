import random
from pathlib import Path
from typing import Any, Tuple

from nonebot import on_fullmatch, on_regex
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.params import Fullmatch, RegexGroup
from nonebot.plugin import PluginMetadata

from migang.core import CDItem, CountItem

from .model import ImageData

__plugin_meta__ = PluginMetadata(
    name="最终幻想14图库",
    description="狒狒各类种族的图库",
    usage="""
usage：
    图库来源：
        - mirapri
        - 光之收藏家
        - 露儿
        - 其他？
    指令：
        /晚安   晚安~
        /早安   早安~来张獭图吧
        /(猫男，猫娘，龙男，龙娘，人女，人男，母肥，公肥，女精，男精，鲁加男，鲁加女，兔娘，兔男，大猫)   云吸xx
        (例如 /猫娘)
""".strip(),
    extra={
        "unique_name": "migang_ffxiv_image",
        "example": "/猫娘",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_aliases__ = ["狒狒图库"]
__plugin_category__ = "好看的"
__plugin_count__ = CountItem(20, hint="今天看的太多啦，明天再来吧")
__plugin_cd__ = CDItem(3, hint="看的太快啦，[_剩余时间_]s后再看吧")

DB_PATH = Path(__file__).parent / "imagedata.db"
image_data = ImageData(DB_PATH)

mrltla = on_regex(r"^[/-](猫|人|龙|兔|鲁家|奥拉)(\S)?$", priority=5, block=True)
lalafell = on_regex(r"^[/-](肥|母|公|拉拉)肥$", priority=5, block=True)
hrothgar = on_fullmatch(("/大猫", "-大猫"), priority=5, block=True)
elezen = on_regex(r"^[/-](男|女)精$", priority=5, block=True)

morning_night = on_fullmatch(("/早安", "-早安", "/晚安", "-晚安"), priority=5, block=True)

race_to_table = {
    "猫": "miqote",
    "人": "hyur",
    "龙": "aura",
    "奥拉": "aura",
    "兔": "viera",
    "鲁家": "roegadyn",
    "肥": "lalafell",
    "大猫": "hrothgar",
    "精": "elezen",
}


@mrltla.handle()
async def _(reg_group: Tuple[Any, ...] = RegexGroup()):
    table = race_to_table[reg_group[0]]
    msg = reg_group[1]
    if msg == "男":
        table = table + "m"
    elif msg != "娘" and msg != "女":
        table = random.choice([table, table + "m"])
    await mrltla.send(MessageSegment.image(await image_data.get_random_image(table)))


@lalafell.handle()
async def _(reg_group: Tuple[Any, ...] = RegexGroup()):
    table = race_to_table["肥"]
    msg = reg_group[0]
    if msg == "公":
        table = table + "m"
    elif msg != "母":
        table = random.choice([table, table + "m"])
    await lalafell.send(MessageSegment.image(await image_data.get_random_image(table)))


@hrothgar.handle()
async def _():
    table = race_to_table["大猫"]
    await hrothgar.send(MessageSegment.image(await image_data.get_random_image(table)))


@elezen.handle()
async def _(reg_group: Tuple[Any, ...] = RegexGroup()):
    table = race_to_table["精"]
    msg = reg_group[0]
    if msg == "男":
        table = table + "m"
    await elezen.send(MessageSegment.image(await image_data.get_random_image(table)))


@morning_night.handle()
async def _(msg: str = Fullmatch()):
    await morning_night.send(
        MessageSegment.image(
            await image_data.get_random_image("night" if msg[1] == "晚" else "morning")
        )
    )
