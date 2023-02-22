"""网络环境可能导致无法访问
"""
import os
import re

import aiohttp
from bs4 import BeautifulSoup
from nonebot.log import logger
from nonebot import on_startswith
from fake_useragent import UserAgent
from nonebot.params import Startswith
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageEvent,
    MessageSegment,
    GroupMessageEvent,
)

__plugin_meta__ = PluginMetadata(
    name="PDF搜索",
    description="PDF搜索",
    usage="""
usage：
    搜pdf xxx
""".strip(),
    extra={
        "unique_name": "migang_pdf_search",
        "example": "搜pdf xxx",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_aliases__ = ["pdf搜索"]
__plugin_category__ = "一些工具"

pdf_search = on_startswith(("搜pdf", "/pdf"), priority=5, block=True, ignorecase=True)

base_url = "https://z-lib.is/"


@pdf_search.handle()
async def _(bot: Bot, event: MessageEvent, cmd: str = Startswith()):
    keyword = event.get_plaintext().removeprefix(cmd).strip()
    try:
        async with aiohttp.ClientSession() as client:
            html = await (
                await client.get(
                    os.path.join(base_url, "s"),
                    timeout=10,
                    params={"q": keyword},
                    headers={
                        "user-agent": UserAgent(browsers=["chrome", "edge"]).random
                    },
                )
            ).text()
        soup = BeautifulSoup(html, "lxml")
        divs = soup.find("div", {"id": "searchResultBox"}).find_all(
            "div", {"class": "resItemBox resItemBoxBooks exactMatch"}
        )
        texts = [
            MessageSegment.node_custom(
                user_id=bot.self_id, nickname="无情的搜索机器", content="搜索到以下结果"
            )
        ]
        count = 0
        total = len(divs)
        for div in divs[:3]:
            count += 1
            name = div.find("h3").get_text().strip()
            href = div.find("h3").find("a", href=True)["href"]
            first_div = div.find("table").find("table").find("div")
            publisher = (
                first_div.get_text().strip()
                if re.search('.*?title="Publisher".*?', str(first_div))
                else None
            )
            authors = div.find("div", {"class": "authors"}).get_text().strip()

            texts.append(
                MessageSegment.node_custom(
                    user_id=bot.self_id,
                    nickname="无情的搜索机器",
                    content=f"""
    {count}.
    [名字] {name}
    [作者] {authors if authors else ""}
    [出版社] {publisher if publisher else ""}
    URL:{base_url + href}
            """.strip(),
                )
            )
    except Exception as e:
        logger.warning(f"pdf搜索错误 {keyword}: {e}")
        await pdf_search.finish("pdf搜索当前不可用")
    if count == 0:
        await pdf_search.finish("未搜索到结果，试着换个关键词吧~")
    else:
        texts.append(
            MessageSegment.node_custom(
                user_id=bot.self_id,
                nickname="无情的搜索机器",
                content=f"共{total}个结果，仅显示前3个" if total > count else f"共{count}个结果",
            )
        )
    if isinstance(event, GroupMessageEvent):
        await bot.send_forward_msg(group_id=event.group_id, messages=texts)
    else:
        await bot.send_forward_msg(user_id=event.user_id, messages=texts)
