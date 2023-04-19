from time import time
from typing import Any, Tuple

from nonebot.matcher import Matcher
from nonebot.params import RegexGroup
from nonebot.plugin import PluginMetadata
from nonebot import on_regex, on_fullmatch
from nonebot.adapters.onebot.v11 import MessageSegment

from migang.core import ConfigItem, get_config

from .render_pic import render
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
    extra={
        "unique_name": "migang_weather",
        "example": "宁波天气\n海都天气\n天气森都\n/et",
        "author": "migang",
        "version": 0.1,
    },
)


__plugin_category__ = "一些工具"

__plugin_config__ = (
    ConfigItem(
        key="api_key",
        initial_value=None,
        description="参考 https://github.com/kexue-z/nonebot-plugin-heweather 获取api_key",
    ),
    ConfigItem(
        key="api_type",
        initial_value=0,
        default_value=0,
        description="0 = 普通版(3天天气预报) 1 = 个人开发版(7天天气预报) 2 = 商业版 (7天天气预报)",
    ),
)


weather = on_regex(r".{0,10}?(.*)的?天气(.{0,10})", priority=5, block=True)
eorzean_time = on_fullmatch("/et", priority=5, block=True)


@weather.handle()
async def _(matcher: Matcher, reg_group: Tuple[Any, ...] = RegexGroup()):
    city = reg_group[0] or reg_group[1]
    if city:
        if w := get_eorzean_weather(city):
            await weather.finish(w)
        w_data = Weather(
            city_name=city,
            api_key=await get_config("api_key"),
            api_type=await get_config("api_type"),
        )
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
