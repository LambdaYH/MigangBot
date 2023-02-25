import os
from pathlib import Path
from asyncio import sleep
from datetime import datetime
import anyio
from lxml import etree

from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot_plugin_htmlrender import template_to_pic
import aiohttp
from fake_useragent import UserAgent
import ujson

template_path = Path(__file__).parent / "templates"


async def get_data():
    for i in range(3):
        try:
            today = datetime.today()
            async with aiohttp.ClientSession(json_serialize=ujson.dumps) as client:
                r = await client.get(
                    f"https://baike.baidu.com/cms/home/eventsOnHistory/{today.month:02}.json",
                    headers={
                        "user-agent": UserAgent(browsers=["chrome", "edge"]).random
                    },
                    timeout=7,
                )
                data = await r.json(content_type=None)
            today_events = data[f"{today.month:02}"][f"{today.month:02}{today.day:02}"]
            ret = [
                {
                    "year": event["year"],
                    "title": etree.HTML(event["title"]).xpath("string(.)").rstrip("\n"),
                }
                for event in today_events
            ]
            return ret
        except Exception as e:
            sleep(0.5)
            logger.warning(f"历史上的今天抓取失败，重试次数{i} : {e}")


async def get_today_in_history() -> bytes:
    event_list = await get_data()
    event_list.reverse()
    return await template_to_pic(
        template_path=template_path,
        template_name="todayinhistory.html",
        templates={
            "event_list": event_list,
            "today_date": datetime.now().strftime("%m月%d日"),
        },
        pages={
            "viewport": {"width": 100, "height": 100},
        },
    )


async def get_todayinhistory_image(path: Path) -> MessageSegment:
    date = datetime.now().date()
    # for file in os.listdir(path):
    #     if f"{date}.png" != file:
    #         (path / file).unlink()
    if f"{date}.png" in os.listdir(path):
        return MessageSegment.image(path / f"{date}.png")
    img = await get_today_in_history()
    async with await anyio.open_file(path / f"{date}.png", "wb") as wf:
        await wf.write(img)
    return MessageSegment.image(img)
