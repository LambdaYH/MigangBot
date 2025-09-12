from time import time
from typing import Any, Tuple

from nonebot.matcher import Matcher
from nonebot.params import RegexGroup
from nonebot.plugin import PluginMetadata
from nonebot import on_regex, on_fullmatch
from nonebot.adapters.onebot.v11 import MessageSegment

from migang.core import ConfigItem, get_config

from .render_pic import render
from .config import plugin_config
from .eorzean_weather import get_eorzean_weather
from .weather_data import Weather, CityNotFoundError, NoWeatherDataError

__plugin_meta__ = PluginMetadata(
    name="天气",
    description="使用和风天气API查询天气，但是能查艾欧泽亚",
    usage="""
usage：
    指令：
        查询天气：xx天气/天气xx，支持地名和艾欧泽亚地名
        查询艾欧泽亚时间：/et
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)


__plugin_category__ = "一些工具"


weather = on_regex(r"^.{0,10}?(.{0,10})的?天气(.{0,10})$", priority=5, block=True)
eorzean_time = on_fullmatch("/et", priority=5, block=True)


@weather.handle()
async def _(matcher: Matcher, reg_group: Tuple[Any, ...] = RegexGroup()):
    city = reg_group[0] or reg_group[1]
    if city:
        if w := get_eorzean_weather(city):
            await weather.finish(w)
        w_data = Weather(city_name=city, api_type=plugin_config.qweather_apitype)
        try:
            await w_data.load_data()
        except (CityNotFoundError, NoWeatherDataError):
            matcher.block = False
            await weather.finish()

        await weather.finish(MessageSegment.image(await render(w_data)))


@eorzean_time.handle()
async def _():
    month, day, hour, minite, second = get_eorzea_time(time())
    await eorzean_time.send(
        f"艾欧泽亚时间：{month:02}月{day:02}日 {hour:02}:{minite:02}:{second:02}"
    )


EORZEA_TIME_CONSTANT = 3600 / 175


def get_eorzea_time(unixSeconds):
    eorzeaTime = unixSeconds * EORZEA_TIME_CONSTANT
    month = int((eorzeaTime / 2764800) % 12) + 1
    day = int((eorzeaTime / 86400) % 32) + 1
    hour = int(eorzeaTime / 3600 % 24)
    minite = int(eorzeaTime / 60 % 60)
    second = int(eorzeaTime / 1 % 60)
    return month, day, hour, minite, second
