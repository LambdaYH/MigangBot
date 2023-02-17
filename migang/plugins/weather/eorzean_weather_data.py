import csv
from io import StringIO
from typing import Dict, List, Any

import aiohttp
from nonebot.log import logger
from nonebot import Driver, get_driver
from nonebot_plugin_apscheduler import scheduler

from migang.core import DATA_PATH
from migang.utils.file import async_load_data, async_save_data

weather_idx_file = DATA_PATH / "eorzean_weather" / "weather_idx.json"
location_idx_file = DATA_PATH / "eorzean_weather" / "location_idx.json"
weather_rate_file = DATA_PATH / "eorzean_weather" / "weather_rate_idx.json"
alter_name_file = DATA_PATH / "eorzean_weather" / "alter_name.json"

TerritoryTypeUrl = "https://raw.githubusercontent.com/thewakingsands/ffxiv-datamining-cn/master/TerritoryType.csv"
placeNameUrl = "https://raw.githubusercontent.com/thewakingsands/ffxiv-datamining-cn/master/PlaceName.csv"
weatherRateUrl = "https://raw.githubusercontent.com/thewakingsands/ffxiv-datamining-cn/master/WeatherRate.csv"
weatherUrl = "https://raw.githubusercontent.com/thewakingsands/ffxiv-datamining-cn/master/Weather.csv"

alter_name: Dict[str, str] = {}
weather_idx: List[str] = []
location_idx: List[str] = {}
weather_rate_idx: Dict[str, List[Dict[str, Any]]] = {}

driver: Driver = get_driver()


async def read_code_location():
    code_location = {}
    async with aiohttp.ClientSession() as client:
        data = await (await client.get(url=placeNameUrl, timeout=15)).text()
    c = csv.reader(StringIO(data))
    for row in c:
        if c.line_num <= 3:
            continue
        code_location[row[0]] = row[1]
    return code_location


async def read_alter_name():
    return await async_load_data(alter_name_file)


async def update_weather():
    global weather_idx
    async with aiohttp.ClientSession() as client:
        data = await (await client.get(url=weatherUrl, timeout=15)).text()
    c = csv.reader(StringIO(data))
    weather_idx.clear()
    for row in c:
        if c.line_num <= 3:
            continue
        weather_idx.append(row[2])
    await async_save_data(weather_idx, weather_idx_file)


async def update_weather_rate():
    global weather_rate_idx
    async with aiohttp.ClientSession() as client:
        data = await (await client.get(url=weatherRateUrl, timeout=15)).text()
    c = csv.reader(StringIO(data))
    for row in c:
        if c.line_num <= 3:
            continue
        temp = 0
        weather_rate_idx[row[0]] = []
        for i in range(len(row) - 1):
            if temp == 100:
                break
            if i % 2 == 1:
                temp += int(row[i + 1])
                weather_rate_idx[row[0]].append({"weather": int(row[i]), "rate": temp})
    await async_save_data(weather_rate_idx, weather_rate_file)


async def update_territory_info():
    global location_idx
    async with aiohttp.ClientSession() as client:
        data = await (await client.get(url=TerritoryTypeUrl, timeout=15)).text()
    c = csv.reader(StringIO(data))
    codeLocation = await read_code_location()
    a_n = await read_alter_name()
    for row in c:
        if c.line_num <= 3:
            continue
        if row[6] != 0:
            if codeLocation.get(row[6]):
                LocationName = codeLocation.get(row[6])
                if location_idx.get(LocationName) or "_" in row[1]:
                    continue
                location_idx[LocationName] = {"weather_rate": row[13]}
    await async_save_data(location_idx, location_idx_file)
    for name in location_idx:
        if not a_n.get(name):
            a_n[name] = []
    for k, v in a_n.items():
        for name in v:
            alter_name[name] = k
    await async_save_data(a_n, alter_name_file)


async def load_data():
    global weather_idx
    global location_idx
    global weather_rate_idx
    weather_idx_file.parent.mkdir(parents=True, exist_ok=True)
    weather_idx = list(await async_load_data(weather_idx_file))
    location_idx = await async_load_data(location_idx_file)
    weather_rate_idx = await async_load_data(weather_rate_file)

    a_n = await read_alter_name()
    for k, v in a_n.items():
        for name in v:
            alter_name[name] = k


async def update_eorzean_weather_data():
    try:
        await update_weather()
        await update_weather_rate()
        await update_territory_info()
    except Exception as e:
        logger.warning(f"艾欧泽亚天气数据更新异常，加载现有数据：{e}")
        await load_data()


@driver.on_startup
async def _():
    if (
        weather_idx_file.exists()
        and location_idx_file.exists()
        and weather_rate_file.exists()
    ):
        await load_data()
    else:
        await update_eorzean_weather_data()


@scheduler.scheduled_job(
    "cron",
    week=3,
    hour=4,
    minute=22,
)
async def _():
    await update_eorzean_weather_data()
