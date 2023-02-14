import re
import asyncio
from typing import Coroutine, Optional, Tuple, List, Union, Callable

import aiohttp
from aiocache import cached
from nonebot import on_regex
from nonebot.matcher import Matcher
from nonebot.params import RegexMatched
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, ActionFailed
from nonebot.log import logger
from nonebot.adapters.onebot.v11.permission import GROUP

from migang.core import TaskItem, check_task, GroupTaskChecker

from .bilibili import (
    BVID_PATTERN,
    AID_PATTERN,
    bilibili_bangumi_keywords,
    bilibili_live_keywords,
    bilibili_video_keywords,
    get_bangumi_detail,
    get_live_summary,
    get_video_detail,
)
from .github import get_github_repo_card, github_urls
from .weibo import get_weibo_info, weibo_urls
from .utils import cache

__plugin_meta__ = PluginMetadata(
    name="群内链接解析",
    description="解析群聊消息中的各类链接",
    usage="""
usage：
    检测群内各类链接后自动解析
    目前支持：
        B站
        微博
        Github
""".strip(),
    extra={
        "unique_name": "migang_url_parse",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)

BILIBILI_TASK = "url_parse_bilibili"
GITHUB_TASK = "url_parse_github_repo_card"
WEIBO_TASK = "url_parse_weibo_parse"


__plugin_hidden__ = True
__plugin_task__ = (
    TaskItem(task_name=BILIBILI_TASK, name="B站链接解析", default_status=True),
    TaskItem(task_name=GITHUB_TASK, name="github链接解析", default_status=True),
    TaskItem(task_name=WEIBO_TASK, name="微博链接解析", default_status=True),
)

URL_PATTERN = re.compile(
    r"https?:[//|\\/\\/](?:[a-zA-Z]|[0-9]|[$-_@.&#+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
)

ALIAS_DOMAIN = (
    "https://b23.tv",
    "https://m.bilibili.com",
    "https://bilibili.com",
)

url_parse = on_regex(pattern=URL_PATTERN, permission=GROUP, priority=22, block=False)
bilibili_bvid = on_regex(
    pattern=BVID_PATTERN,
    permission=GROUP,
    priority=23,
    rule=GroupTaskChecker(BILIBILI_TASK),
)
bilibili_aid = on_regex(
    pattern=AID_PATTERN,
    permission=GROUP,
    priority=24,
    rule=GroupTaskChecker(BILIBILI_TASK),
    block=False,
)

func_dict = {
    get_video_detail: BILIBILI_TASK,
    get_bangumi_detail: BILIBILI_TASK,
    get_live_summary: BILIBILI_TASK,
    get_github_repo_card: GITHUB_TASK,
    get_weibo_info: WEIBO_TASK,
}


# transfer b23.tv to bilibili.com
@cached(ttl=300)
async def get_url(url):
    async with aiohttp.ClientSession() as client:
        r = await client.head(url, timeout=15, allow_redirects=False)
        if 300 <= r.status <= 399:
            return r.headers["location"]
    return url


def get_function(url: str) -> Optional[Callable]:
    if "bilibili" in url:
        if url.startswith(bilibili_video_keywords):
            return get_video_detail
        elif url.startswith(bilibili_bangumi_keywords):
            return get_bangumi_detail
        elif url.startswith(bilibili_live_keywords):
            return get_live_summary
    elif url.startswith(github_urls):
        return get_github_repo_card
    elif "weibo" in url and url.startswith(weibo_urls):
        return get_weibo_info
    return None


@url_parse.handle()
async def _(matcher: Matcher, event: GroupMessageEvent):
    msg = str(event.message)
    if msg.startswith("【FF14/时尚品鉴】"):
        return
    url_list = set(URL_PATTERN.findall(msg))
    tasks: List[Coroutine] = []
    for url in url_list:
        url = url.replace("\/", "/")
        if url.startswith(ALIAS_DOMAIN):
            url = await get_url(url)
        url = url.rstrip("&")
        if url.startswith("http:"):
            url = url.replace("http:", "https:", 1)
        if cache.check(group_id=event.group_id, url=url):
            continue
        func = get_function(url=url)
        if (func is not None) and check_task(event.group_id, func_dict[func]):
            tasks.append(func(url))
    if tasks:
        matcher.stop_propagation()
    else:
        return
    ret: List[Union[Tuple[Message, str], str]] = await asyncio.gather(
        *tasks, return_exceptions=True
    )
    for msg in ret:
        if isinstance(msg, Tuple):
            if cache.add(group_id=event.group_id, url=msg[1]):
                try:
                    await url_parse.send(msg[0])
                except ActionFailed:
                    logger.warning(f"发送消息 {msg[0]} 失败")
        else:
            logger.warning(f"链接解析失败：{msg}")


@bilibili_aid.handle()
@bilibili_bvid.handle()
async def _(matcher: Matcher, event: GroupMessageEvent, id: str = RegexMatched()):
    url = f"https://www.bilibili.com/video/{id}"
    if cache.check(group_id=event.group_id, url=url):
        await matcher.finish()
    if (func := get_function(url=url)) is not None:
        matcher.stop_propagation()
        try:
            msg, link = await func(url)
            if cache.add(group_id=event.group_id, url=link):
                try:
                    await matcher.send(msg)
                    cache.add(group_id=event.group_id, url=link)
                except ActionFailed:
                    logger.warning(f"发送消息 {msg[0]} 失败")
        except Exception as e:
            logger.warning(f"链接解析失败：{url}：{e}")
