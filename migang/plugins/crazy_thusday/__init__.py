"""
https://github.com/MinatoAquaCrews/nonebot_plugin_crazy_thursday
"""
import random
from typing import List
from pathlib import Path

import anyio
import ujson as json
from nonebot import on_regex
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata
from nonebot.params import Depends, RegexMatched

from .config import *
from .config import crazy_config

__plugin_meta__ = PluginMetadata(
    name="疯狂星期四",
    description="随机输出KFC疯狂星期四文案",
    usage="""
usage：
    随机输出KFC疯狂星期四文案
    指令：
        疯狂星期[一|二|三|四|五|六|日]
        狂乱[月|火|水|木|金|土|日]曜日
""".strip(),
    extra={
        "unique_name": "migang_crazy_thusday",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_category__ = "好玩的"
crazy_cn = on_regex(pattern=r"^疯狂星期\S$", priority=15, block=False)
crazy_jp = on_regex(pattern=r"^狂乱\S曜日$", priority=15, block=False)


async def get_weekday_cn(arg: str = RegexMatched()) -> str:
    return arg[-1].replace("天", "日")


async def get_weekday_jp(arg: str = RegexMatched()) -> str:
    return arg[2]


@crazy_cn.handle()
async def _(matcher: Matcher, weekday: str = Depends(get_weekday_cn)):
    await matcher.finish(await rndKfc(weekday))


@crazy_jp.handle()
async def _(matcher: Matcher, weekday: str = Depends(get_weekday_jp)):
    await matcher.finish(await rndKfc(weekday))


async def rndKfc(day: str) -> str:
    # jp en cn
    tb: List[str] = [
        "月",
        "Monday",
        "一",
        "火",
        "Tuesday",
        "二",
        "水",
        "Wednesday",
        "三",
        "木",
        "Thursday",
        "四",
        "金",
        "Friday",
        "五",
        "土",
        "Saturday",
        "六",
        "日",
        "Sunday",
        "日",
    ]
    if day not in tb:
        return "你给的似乎是宇宙收缩后的时间呢?"

    # Get the weekday group index
    idx: int = int(tb.index(day) / 3) * 3

    # json数据存放路径
    path: Path = crazy_config.crazy_path / "post.json"

    # 将json对象加载到数组
    async with await anyio.open_file(path, "r", encoding="utf-8") as f:
        kfc = json.loads(await f.read()).get("post")

        # 随机选取数组中的一个对象，并替换日期
        return (
            random.choice(kfc)
            .replace("木曜日", tb[idx] + "曜日")
            .replace("Thursday", tb[idx + 1])
            .replace("thursday", tb[idx + 1])
            .replace("星期四", "星期" + tb[idx + 2])
            .replace("周四", "周" + tb[idx + 2])
            .replace("礼拜四", "礼拜" + tb[idx + 2])
        )
