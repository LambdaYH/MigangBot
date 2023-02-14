import re
import html
from typing import Tuple

from lxml import etree
from aiocache import cached
import aiohttp

from fake_useragent import UserAgent
from nonebot.adapters.onebot.v11 import MessageSegment, Message

AID_PATTERN = re.compile(r"(av|AV)\d+")
BVID_PATTERN = re.compile(r"(BV|bv)([a-zA-Z0-9])+")

bilibili_video_keywords = ("https://www.bilibili.com/video",)
bilibili_bangumi_keywords = ("https://www.bilibili.com/bangumi",)
bilibili_live_keywords = ("https://live.bilibili.com",)


@cached(ttl=240)
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
        details = await (await client.get(api_url, timeout=15)).json()
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


@cached(ttl=240)
async def get_bangumi_detail(url: str) -> Tuple[Message, str]:
    async with aiohttp.ClientSession() as client:
        text = await (
            await client.get(
                url,
                headers={"User-Agent": UserAgent(browsers=["chrome", "edge"]).random},
                timeout=15,
                allow_redirects=True,
            )
        ).text()
    dom = etree.HTML(text, etree.HTMLParser())
    title = (
        dom.xpath("//div[@class='media-wrapper']/h1/text()")[0]
        + " ["
        + dom.xpath(
            "//div[@class='media-wrapper']/div[@id='media_module']/div[@class='media-right']/div[@class='pub-wrapper']/a[@class='home-link']/text()"
        )[0]
        + "-"
        + dom.xpath(
            "//div[@class='media-wrapper']/div[@id='media_module']/div[@class='media-right']/div[@class='pub-wrapper']/span[@class='pub-info']/text()"
        )[0]
        + "]"
    )
    description = html.unescape(
        dom.xpath(
            "//div[@class='media-wrapper']/div[@id='media_module']/div[@class='media-right']/div/a/span[@class='absolute']/text()"
        )[0]
    )
    cover = dom.xpath("/html/head/meta[@property='og:image']/@content")[0]
    ep = re.search(r"(ss|ep)\d+", url).group()
    link = re.sub(
        r"(ss|ep)\d+",
        ep,
        dom.xpath("/html/head/meta[@property='og:url']/@content")[0],
    )
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


@cached(ttl=240)
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
            )
        ).json()
        if r["code"] == 0:
            uid = r["data"]["uid"]
        else:
            return "↑ 直播间不存在~", link
        r = await client.head("https://www.bilibili.com/", headers=headers)
        r = await (
            await client.get(
                f"https://api.bilibili.com/x/space/acc/info?mid={uid}",
                timeout=15,
                headers=headers,
                cookies=r.cookies,
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
