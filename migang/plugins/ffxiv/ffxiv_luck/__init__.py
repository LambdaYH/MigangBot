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


def get_page_num(user_id: int):
    today = datetime.date.today()
    formatted_today = int(today.strftime("%y%m%d"))
    strnum = str(formatted_today * user_id)

    md5 = hashlib.md5()
    md5.update(strnum.encode("utf-8"))
    res = md5.hexdigest()

    return int(res.upper(), 16) % 100 + 1


@ffxiv_luck.handle()
async def _(event: Union[GroupMessageEvent, PrivateMessageEvent]):
    await ffxiv_luck.send(
        MessageSegment.image(img_path / path_list[get_page_num(event.user_id)])
    )
