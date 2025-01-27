import hashlib
import datetime
from pathlib import Path
from typing import Union

from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import (
    MessageSegment,
    GroupMessageEvent,
    PrivateMessageEvent,
)

from migang.utils.date import is_new_year

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="最终幻想14Luck",
    description="luck",
    usage="""
usage：
    指令：
        /luck
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_category__ = "FF14"

ffxiv_luck = on_fullmatch(("/luck", "、luck"), priority=5, block=True)

img_path = Path(__file__).parent / "images"
path_list = [img.name for img in img_path.iterdir()]
path_list.sort(key=lambda name: int(name.removesuffix(".jpg")))


def get_page_num(user_id: int):
    today = datetime.date.today()

    formatted_today = int(today.strftime("%y%m%d"))
    strnum = str(formatted_today * user_id)

    md5 = hashlib.md5()
    md5.update(strnum.encode("utf-8"))
    res = md5.hexdigest()
    # 春节
    if is_new_year():
        daji = [0, 7, 8, 9, 10, 11, 12, 61, 77, 79, 84, 88, 89, 85, 86, 98]
        return daji[int(res.upper(), 16) % len(daji)]

    return int(res.upper(), 16) % len(path_list)


@ffxiv_luck.handle()
async def _(event: Union[GroupMessageEvent, PrivateMessageEvent]):
    await ffxiv_luck.send(
        MessageSegment.image(img_path / path_list[get_page_num(event.user_id)]),
        at_sender=True,
    )
