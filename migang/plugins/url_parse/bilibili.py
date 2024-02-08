import re
import html
import asyncio
from typing import Tuple

import aiohttp
from lxml import etree
from nonebot.log import logger
from fake_useragent import UserAgent
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from migang.utils.http import get_signed_params

from .utils import parser_manager

AID_PATTERN = re.compile(r"(av|AV)\d+")
BVID_PATTERN = re.compile(r"(BV|bv)([a-zA-Z0-9])+")

BANGUMI_API_URL = "https://api.bilibili.com/pgc/view/web/season"


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
        + MessageSegment.image(cover)
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
        + MessageSegment.image(cover)
        + "\n"
        + f"URL:{link}"
    )
    return msg, link


@parser_manager(
    task_name="url_parse_bilibili", startswith=("https://live.bilibili.com",), ttl=240
)
async def get_live_summary(url: str) -> Tuple[Message, str]:
    link = re.search(r"(https|http)://live.bilibili.com/\d+", url)
    if link:
        link = link.group()
        roomid = re.search(r"\d+", link).group()
    else:
        raise Exception("no link found")
    async with aiohttp.ClientSession() as client:
        headers = {"User-Agent": UserAgent(browsers=["chrome", "edge"]).random}
        r = await (
            await client.get(
                f"https://api.live.bilibili.com/room/v1/Room/room_init?id={roomid}",
                timeout=15,
                headers=headers,
            )
        ).json()
        if r["code"] == 0:
            uid = r["data"]["uid"]
        else:
            return "↑ 直播间不存在~", link
        await asyncio.sleep(0.1)
        r = await (
            await client.get(
                f"https://api.bilibili.com/x/space/acc/info",
                timeout=15,
                headers=headers,
                params=await get_signed_params(
                    {"mid": uid, "order": "pubdate", "pn": 1, "ps": 5}
                ),
            )
        ).json()
    if r["code"] == 0:
        title = r["data"]["live_room"]["title"]
        up = r["data"]["name"]
        cover = r["data"]["live_room"]["cover"]
        status = r["data"]["live_room"]["liveStatus"]
        link = f"https://live.bilibili.com/{roomid}"
    else:
        raise Exception("cannot fetch the detail of this live room")

    msg = (
        ("[直播中]" if status == 1 else "[未开播]")
        + "\n"
        + f"[标题] {title}\n"
        + f"[主播] {up}\n"
        + "[封面] "
        + MessageSegment.image(cover)
        + "\n"
        + f"URL:{link}"
    )
    return msg, link
