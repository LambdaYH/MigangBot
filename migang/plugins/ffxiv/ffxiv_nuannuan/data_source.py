import pytz
import re
import math
import asyncio
from io import BytesIO
from typing import List, Dict
from datetime import datetime

import aiohttp
import aiofiles
from tenacity import retry, stop_after_attempt, wait_random
from PIL import Image
from nonebot import get_driver
from fake_useragent import UserAgent
from nonebot.log import logger
from nonebot_plugin_htmlrender import get_new_page
from nonebot_plugin_apscheduler import scheduler
from playwright.async_api import TimeoutError

from migang.core import DATA_PATH

nuannuan_path = DATA_PATH / "ffxiv" / "nuannuan" / "nuannuan.png"
nuannuan_path.parent.mkdir(exist_ok=True, parents=True)
nuannuan_text = []
url = "https://docs.qq.com/sheet/DY2lCeEpwemZESm5q?tab=dewveu&c=A1A0A0"

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1343.33"
}

nuannuan_start_time = datetime(
    year=2018, month=1, day=30, hour=16, minute=0, second=0
).astimezone(pytz.timezone("Asia/Shanghai"))


def get_data():
    return nuannuan_path, nuannuan_text


async def get_nuannuan_image() -> None:
    try:
        async with get_new_page(viewport={"width": 2560, "height": 1080}) as page:
            await page.goto(url)
            card = await page.wait_for_selector(".operate-board", timeout=60 * 1000)
            img = await card.screenshot()
            if img:
                crop_image = Image.open(BytesIO(img))
                crop_image = crop_image.crop(
                    (80, 33, 779, min(1074, crop_image.size[1] - 33))
                )
                with BytesIO() as buf:
                    crop_image.save(buf, format="PNG")
                    async with aiofiles.open(nuannuan_path, "wb") as f:
                        await f.write(buf.getvalue())
    except TimeoutError as e:
        logger.warning(f"获取暖暖图片失败：{e}")


async def get_video_id(mid: int) -> str:
    try:
        # 获取用户信息最新视频的前五个，避免第一个视频不是攻略ps=5处修改
        async with aiohttp.ClientSession() as client:
            headers = {"user-agent": UserAgent(browsers=["chrome", "edge"]).random}
            url = f"https://api.bilibili.com/x/space/arc/search?mid={mid}&order=pubdate&pn=1&ps=5"
            r = await client.head("https://www.bilibili.com/", headers=headers)
            r = await (await client.get(url, headers=headers, cookies=r.cookies)).json()
            video_list = r["data"]["list"]["vlist"]
            for i in video_list:
                if re.match(r"【FF14\/时尚品鉴】第\d+期 满分攻略", i["title"]):
                    return i["bvid"]
    except Exception as e:
        logger.warning(f"获取暖暖动态失败：{e}")
    return None


async def extract_nn(bvid: str) -> Dict[str, str]:
    try:
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        async with aiohttp.ClientSession() as client:
            r = await (await client.get(url, timeout=5)).json()
            if r["code"] == 0:
                url = f"https://www.bilibili.com/video/{bvid}"
                title = r["data"]["title"]
                desc = r["data"]["desc"]
                text = desc.replace("个人攻略网站", "游玩C攻略站")
                image = r["data"]["pic"]
                res_data = {
                    "url": url,
                    "title": title,
                    "content": text,
                    "image": image,
                }
                return res_data
    except Exception as e:
        logger.warning(f"获取暖暖动态内容失败: {e}")
    return None


def format_nn_text(text: str) -> List[str]:
    text = text[text.find("主题：") : text.rfind("\n\n")]
    text = re.sub(r"\n{2,10}", "\n\n", text)
    text_list = text.split("\n\n")
    return [t for t in text_list if re.search("【[\s\S]+】", t)]


async def get_nuannuan_text() -> None:
    bvid = await get_video_id(15503317)
    # 获取数据
    res_data = await extract_nn(bvid)
    if not res_data:
        msg = ["获取暖暖文字信息失败"]
    else:
        phase = re.search(r"【FF14/时尚品鉴】第(\d+)期[\S\s]*", res_data["title"]).group(1)
        theme_s = res_data["content"].find("主题：")
        cur_phase = str(
            math.ceil(
                (
                    datetime.now(pytz.timezone("Asia/Shanghai")) - nuannuan_start_time
                ).days
                / 7
            )
        )
        msg = [
            (f"第 {phase} 期\n" if phase == cur_phase else f"第 {phase} 期（已过时）\n")
            + res_data["content"][theme_s : res_data["content"].find("\n", theme_s)]
        ]
        msg += format_nn_text(res_data["content"])
    global nuannuan_text
    nuannuan_text = msg


@get_driver().on_startup
async def _():
    logger.info("正在初始化暖暖数据...")
    if not nuannuan_path.exists():
        asyncio.create_task(get_nuannuan_image())
    asyncio.create_task(get_nuannuan_text())


@scheduler.scheduled_job(
    "cron",
    hour=2,
    minute=8,
)
async def _():
    await asyncio.gather(*[get_nuannuan_image(), get_nuannuan_text()])