import re
from typing import Tuple

import aiohttp
from fake_useragent import UserAgent
from lxml import etree


async def get_baidu(keyword: str) -> Tuple[str, str, str]:
    async with aiohttp.ClientSession() as client:
        r = await client.get(
            f"https://baike.baidu.com/search/word?word={keyword}",
            headers={"User-Agent": UserAgent(browsers=["chrome", "edge"]).random},
            allow_redirects=True,
            timeout=5,
        )
    dom = etree.HTML(await r.text(), etree.HTMLParser())
    content = dom.xpath("//div[@class='lemma-summary']")
    if not content:
        new_url = dom.xpath(
            "//div[@class='content-wrapper']/div/div/ul/li/div[@class='para']/a/@href"
        )
        if not new_url:
            return "", "", ""
        async with aiohttp.ClientSession() as client:
            r = await client.get(
                f"https://baike.baidu.com{new_url[0]}",
                headers={"User-Agent": UserAgent(browsers=["chrome", "edge"]).random},
                timeout=5,
            )
        dom = etree.HTML(await r.text(), etree.HTMLParser())
        content = dom.xpath("//div[@class='lemma-summary']")
        if not content:
            return "", "", ""
    title = dom.xpath(
        "//dd[@class='lemmaWgt-lemmaTitle-title J-lemma-title']/span/h1/text()"
    )[0]
    img_urls = dom.xpath("//div[@class='summary-pic']/a/img/@src")

    msg = content[0].xpath("string(.)").strip().replace("\xa0", "")
    msg = re.sub(r"\[(\d+\-\d+|\d+)]", "", msg)
    msg = re.sub(r"\n+", "\n", msg)
    if img_urls:
        msg += "<div>"
        for img in img_urls:
            msg += f'<img width="50%" src="{img}"/>'
        msg += "</div>"

    return title, msg, None
