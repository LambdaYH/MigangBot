import re
import asyncio
from typing import Tuple, Optional
from time import strftime, localtime

import aiohttp
from yarl import URL
from nonebot.log import logger
from fake_useragent import UserAgent
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from .utils import parser_manager

AID_PATTERN = re.compile(r"(av|AV)\d+")
BVID_PATTERN = re.compile(r"(BV|bv)([a-zA-Z0-9])+")

BANGUMI_API_URL = "https://api.bilibili.com/pgc/view/web/season"
LIVE_API_URL = "https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom"


async def download_image(url: str) -> Optional[bytes]:
    for _ in range(5):
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            referer = f"{URL(url).scheme}://{URL(url).host}/"
            headers = {"referer": referer}
            try:
                resp = await session.get(url, headers=headers)
                # 如果图片无法获取到，直接返回
                if len(await resp.read()) == 0:
                    return None
                # 如果图片格式为 SVG ，先转换为 PNG
                if resp.headers["Content-Type"].startswith("image/svg+xml"):
                    next_url = str(
                        URL("https://images.weserv.nl/").with_query(
                            f"url={url}&output=png"
                        )
                    )
                    return await download_image(next_url)
                return await resp.read()
            except Exception as e:
                logger.warning(f"图片[{url}]下载失败！将重试最多 5 次！\n{e}")
                await asyncio.sleep(10)
    return None


@parser_manager(
    task_name="url_parse_bilibili",
    startswith=("https://www.bilibili.com/video",),
    ttl=240,
)
async def get_video_detail(url: str) -> Tuple[Message, str]:
    aid = re.search(AID_PATTERN, url)
    bvid = re.search(BVID_PATTERN, url)
    if bvid:
        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid.group()}"
    elif aid:
        api_url = f"https://api.bilibili.com/x/web-interface/view?aid={aid.group()[2:]}"
    else:
        raise Exception("找不到bvid或aid")
    async with aiohttp.ClientSession() as client:
        details = await (
            await client.get(
                api_url,
                timeout=15,
                headers={"User-Agent": UserAgent(browsers=["chrome", "edge"]).random},
            )
        ).json()
    if details["code"] != 0:
        raise Exception("cannot fetch video detail")
    details = details["data"]
    title = details["title"]
    description = details["desc"]
    auther = details["owner"]["name"]
    cover = details["pic"]
    link = f"https://www.bilibili.com/video/{details['bvid']}"
    # get part details
    part = re.search(r"(\?|&amp;|&){1}p=(\d+){1}", url)
    if part and part.group(2) != "1":
        title += " [P" + part.group(2) + "]"
        link += f"?p={part.group(2)}"
    msg = (
        f"[标题] {title}\n[作者] {auther}\n"
        + (
            f"[简介] \n{description}"
            if description.strip() != ""
            else f"[简介] {description}"
        )
        + "\n"
        + "[封面] "
        + MessageSegment.image(await download_image(cover))
        + "\n"
        + f"URL:{link}"
    )
    return msg, link


@parser_manager(
    task_name="url_parse_bilibili",
    startswith=("https://www.bilibili.com/bangumi",),
    ttl=240,
)
async def get_bangumi_detail(url: str) -> Tuple[Message, str]:
    ep_id = re.search(r"ep(\d+)", url)
    ss_id = re.search(r"ss(\d+)", url)
    md_id = re.search(r"md(\d+)", url)
    real_url: str
    if ep_id:
        real_url = f"{BANGUMI_API_URL}?ep_id={ep_id.group(1)}"
    elif ss_id:
        real_url = f"{BANGUMI_API_URL}?season_id={ss_id.group(1)}"
    elif md_id:
        real_url = f"{BANGUMI_API_URL}?media_id={md_id.group(1)}"
    else:
        raise Exception("无法获取剧集信息")

    async with aiohttp.ClientSession() as client:
        r = await (
            await client.get(
                real_url,
                headers={"User-Agent": UserAgent(browsers=["chrome", "edge"]).random},
            )
        ).json()
        res = r.get("result")
        if not res:
            logger.warning(f"获取剧集信息：{url}失败：{r}")
            raise Exception("无法获取剧集详细信息")
    title = res["title"]
    description = res["evaluate"]
    if ss_id:
        link = f"https://www.bilibili.com/bangumi/play/{ss_id.group()}"
    elif md_id:
        link = f"https://www.bilibili.com/bangumi/media/{md_id.group()}"
    else:
        epid = ep_id.group(1)
        for i in res["episodes"]:
            if str(i["ep_id"]) == epid:
                title += f"-{i['long_title']}"
                break
        link = f"https://www.bilibili.com/bangumi/play/ep{epid}"
    cover = res["cover"]

    msg = (
        f"[标题] {title}\n"
        + (
            f"[简介] \n{description}"
            if description.strip() != ""
            else f"[简介] {description}" + "\n"
        )
        + "\n"
        + "[封面] "
        + MessageSegment.image(await download_image(cover))
        + "\n"
        + f"URL:{link}"
    )
    return msg, link


@parser_manager(
    task_name="url_parse_bilibili", startswith=("https://live.bilibili.com",), ttl=240
)
async def get_live_summary(url: str) -> Tuple[Message, str]:
    link = re.search(r"live.bilibili.com/(blanc/|h5/)?(\d+)", url)
    if link:
        room_id = link.group(2)
    else:
        raise Exception("no link found")
    async with aiohttp.ClientSession() as client:
        headers = {"User-Agent": UserAgent(browsers=["chrome", "edge"]).random}
        r = await (
            await client.get(
                f"{LIVE_API_URL}?room_id={room_id}",
                timeout=15,
                headers=headers,
            )
        ).json()
        if r["code"] != 0:
            raise Exception("获取直播间信息失败")
        res = r["data"]

    title = res["room_info"]["title"]
    up = res["anchor_info"]["base_info"]["uname"]
    live_status = res["room_info"]["live_status"]
    lock_status = res["room_info"]["lock_status"]
    parent_area_name = res["room_info"]["parent_area_name"]
    area_name = res["room_info"]["area_name"]
    real_status: str
    if lock_status:
        lock_time = res["room_info"]["lock_time"]
        lock_time = strftime("%Y-%m-%d %H:%M:%S", localtime(lock_time))
        real_status = f"[已封禁] 至：{lock_time}\n"
    elif live_status == 1:
        real_status = "[直播中]"
    elif live_status == 2:
        real_status = "[轮播中]"
    else:
        real_status = "[未开播]"
    cover = res["room_info"]["cover"]

    msg = (
        real_status
        + "\n"
        + f"[标题] {title}\n"
        + f"[主播] {up}\n"
        + f"[分区] {parent_area_name} - {area_name}\n"
        + "[封面] "
        + MessageSegment.image(await download_image(cover))
        + "\n"
        + f"URL:https://live.bilibili.com/{room_id}"
    )
    return msg, link
