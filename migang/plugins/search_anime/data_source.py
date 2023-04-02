import time
import asyncio
from typing import List, Union

import aiohttp
import feedparser
from lxml import etree
from nonebot.log import logger


async def from_anime_get_info(key_word: str, max_: int) -> Union[str, List[str]]:
    s_time = time.time()
    try:
        repass = await get_repass(key_word, max_)
    except Exception as e:
        logger.error(f"发生了一些错误：{e}")
        return "发生了一些错误！"
    repass.insert(0, f"搜索 {key_word} 结果（耗时 {int(time.time() - s_time)} 秒）：\n")
    return repass


async def get_repass(key_word: str, max_: int) -> List[str]:
    async with aiohttp.ClientSession() as client:
        put_line = []
        r = await client.get(
            url="https://share.dmhy.org/topics/rss/rss.xml",
            params={"keyword": key_word},
            timeout=5,
        )
        d = feedparser.parse(await r.text())
        max_ = (
            max_
            if max_ < len([e.link for e in d.entries])
            else len([e.link for e in d.entries])
        )
        url_list = [e.link for e in d.entries][:max_]

        async def get_info(url: str):
            try:
                text = await (await client.get(url, timeout=5)).text()
                html = etree.HTML(text)
                magent = html.xpath('.//a[@id="a_magnet"]/text()')[0]
                title = html.xpath(".//h3/text()")[0]
                item = html.xpath('//div[@class="info resource-info right"]/ul/li')
                class_a = (
                    item[0]
                    .xpath("string(.)")[5:]
                    .strip()
                    .replace("\xa0", "")
                    .replace("\t", "")
                )
                size = item[3].xpath("string(.)")[5:].strip()
                put_line.append(
                    "【{}】| {}\n【{}】| {}".format(class_a, title, size, magent)
                )
            except Exception as e:
                logger.error(f"搜番发生错误：{e}")

        await asyncio.gather(*[get_info(url) for url in url_list])
    return put_line
