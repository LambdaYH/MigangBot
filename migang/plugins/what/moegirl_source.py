import re
from typing import Tuple

import aiohttp
from lxml import etree


async def get_moegirl(keyword: str) -> Tuple[str, str, str]:
    async with aiohttp.ClientSession() as client:
        r = await client.get(
            "https://zh.moegirl.org.cn/api.php",
            params={"action": "opensearch", "search": keyword},
            timeout=5,
        )
        search_res = await r.json()
        if not search_res[1]:
            return "", "", None
        title = search_res[1][0]
        url = search_res[3][0]
        r = await client.get(url, timeout=5, allow_redirects=True)
        dom = etree.HTML(await r.text())
        info_box = dom.xpath(
            "//div[@id='mw-content-text']/div[@class='mw-parser-output']/table[contains(@class,'infobox')]"
        )
        if not info_box:
            info_box = dom.xpath(
                "//div[@id='mw-content-text']/div[@class='mw-parser-output']/div[contains(@class,'Tabs') or contains(@class,'infoBox')]"
            )
        if info_box:
            info_box = info_box[0]
            msg = info_box.xpath("./following::p[1]")[0].xpath("string(.)").strip("\n")
        else:
            return "", "", None
            # # 可能是不明确条目，eg. https://zh.moegirl.org.cn/%E6%9A%96%E6%9A%96
            # ele = dom.xpath("//div[@class='mw-parser-output']")
            # msg = ele[0].xpath("string(.)")
            # msg = msg.replace(
            #     f"这是一个消歧义页，罗列了有相同或相近的标题，但内容不同的条目。如果有未列出的条目，欢迎添加。您也可以搜索标题包含【{title}】的条目 或 全站搜索【{title}】。如果您是通过某个无关条目的内部链接而转到本页，希望您能协助修正该处的内部链接，将它指向正确的条目。",
            #     "",
            # ).strip("\n")
            # msg = re.sub(r"\n\n+", "\n\n", msg)
        msg = msg.strip()
        if len(msg) >= 10000 or not msg:
            # 太长了可能爬错了
            return "", "", None
    return title, msg, None
