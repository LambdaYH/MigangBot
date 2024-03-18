import re
import asyncio
import hashlib
from typing import Any, Dict, List
from datetime import datetime, timedelta

import aiohttp
import aiofiles
from croniter import croniter
from pydantic import TypeAdapter
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from migang.core import DATA_PATH

data_dir = DATA_PATH / "schedule_reminder"
image_dir = data_dir / "image"

image_dir.mkdir(exist_ok=True, parents=True)


async def cache_file(msg: Message):
    async with aiohttp.ClientSession() as client:
        await asyncio.gather(
            *[cache_image_url(seg, client) for seg in msg if seg.type == "image"]
        )


async def cache_image_url(seg: MessageSegment, client: aiohttp.ClientSession):
    if url := seg.data.get("url"):
        for _ in range(3):
            try:
                r = await client.get(url)
                data = await r.read()
                break
            except asyncio.TimeoutException:
                await asyncio.sleep(0.5)
        seg.type = "cached_image"
    else:
        return
    hash_ = hashlib.md5(data).hexdigest()
    filename = f"{hash_}.cache"
    cache_file_path = image_dir / filename
    cache_files = [f.name for f in image_dir.iterdir() if f.is_file()]
    if filename not in cache_files:
        async with aiofiles.open(cache_file_path, "wb") as f:
            await f.write(data)
    seg.data = {"file": filename}


async def serialize_message(message: Message) -> List[Dict[str, Any]]:
    await cache_file(message)
    return [seg.__dict__ for seg in message]


def deserialize_message(message: List[Dict[str, Any]]) -> Message:
    for seg in message:
        if seg["type"] == "cached_image":
            seg["type"] = "image"
            seg["data"]["file"] = (image_dir / seg["data"]["file"]).resolve().as_uri()
    return TypeAdapter.validate_python(Message, message)


MONTHDAY = {
    "1": 31,
    "2": 28,
    "3": 31,
    "4": 30,
    "5": 31,
    "6": 30,
    "7": 31,
    "8": 31,
    "9": 30,
    "10": 31,
    "11": 30,
    "12": 31,
}


def cron_parse(cron):
    if not croniter.is_valid(cron):
        return False, None, None, None
    time = datetime.now()
    it = croniter(cron, time)
    return (
        True,
        it.get_next(datetime),
        it.get_next(datetime),
        it.get_next(datetime),
    )


def date_parse(time):
    mode = 0
    if time.endswith("后"):
        mode = 1
    if mode == 0:
        year = re.search(r"[\d+]+年", time)
        month = re.search(r"[\d+]+月", time)
        r = re.search(r"[\d+]+[日|号]", time)
        hour = re.search(r"[\d+]+[点|时]", time)
        min_ = re.search(r"[\d+]+分", time)
        if month:
            timeNow = datetime.now()
            y = timeNow.year
            m = int(month.group().rstrip("月"))
            ri = 1
            if r:
                ri = int(r.group().rstrip("日").rstrip("号"))
            if year:
                y = int(year.group().rstrip("年"))
            # check month and day
            if m < 1 or m > 12 or ri < 1 or ri > 31:
                return False, None
            if m == 2 and ((y % 4 == 0 and y % 100 != 0) or y % 400 == 0):
                if ri > MONTHDAY[str(m)] + 1:
                    return False, None
            elif ri > MONTHDAY[str(m)]:
                return False, None

            if hour:
                h = int(hour.group().rstrip("点").rstrip("时"))
            else:
                h = 0

            if min_:
                mi = int(min_.group().rstrip("分"))
            else:
                mi = 0

            return True, datetime(y, m, ri, h, mi)
        else:
            dayDiff = 0
            if "明天" in time:
                dayDiff = 1
            elif "后天" in time:
                dayDiff = 2
            else:
                day = re.search(r"[\d+]+天后", time)
                if day:
                    dayDiff = int(day.group.rstrip("天后"))
            now = datetime.now()
            timeBase = now + timedelta(days=dayDiff)
            if hour:
                h = int(hour.group().rstrip("点").rstrip("时"))
                if h < 0 or h > 24:
                    return False, None
                timeBase = timeBase.replace(hour=h)
                timeBase = timeBase.replace(minute=0)
            if min_:
                m = int(min_.group().rstrip("分"))
                if m < 0 or m > 60:
                    return False, None
                timeBase = timeBase.replace(minute=m)
            if timeBase == now:
                return False, None
            return True, timeBase
    elif mode == 1:
        day = re.search(r"[\d+]+[天|日]", time)
        hour = re.search(r"[\d+]+[时|小时]", time)
        min_ = re.search(r"[\d+]+[分|分钟]", time)
        dayDiff = 0
        hourDiff = 0
        minDiff = 0
        if day:
            dayDiff = int(day.group().rstrip("天").rstrip("日"))
        if hour:
            hourDiff = int(hour.group().rstrip("时").rstrip("小时"))
        if min_:
            minDiff = int(min_.group().rstrip("分").rstrip("分钟"))
        timeBase = datetime.now() + timedelta(
            days=dayDiff, hours=hourDiff, minutes=minDiff
        )

        return True, timeBase


def interval_parse(interval):
    # m : minites, d: day, h:hour
    inSettings = interval.split(":")
    if len(inSettings) != 2:
        return False, "参数个数错误，参考[m:分钟，d:天数，h:小时数]发送", None
    if inSettings[0] == "m":
        return True, "m", int(inSettings[1])
    elif inSettings[0] == "d":
        return True, "d", int(inSettings[1])
    elif inSettings[0] == "h":
        return True, "h", int(inSettings[1])
    else:
        return False, "类型错误，仅支持[m:分钟，d:天数，h:小时数]", None
