import asyncio
from pathlib import Path
from typing import Tuple, Union

import jinja2
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot_plugin_htmlrender import html_to_pic, template_to_pic
from thefuzz import fuzz

from .baidu_source import get_baidu
from .ffxivwiki_source import get_ffxivwiki
from .jiki_source import get_jiki
from .nbnhhsh_source import get_nbnhhsh

template_path = Path(__file__).parent / "template"

sources_func = {
    "jiki": get_jiki,
    "baidu": get_baidu,
    "nbnhhsh": get_nbnhhsh,
    "ffxivwiki": get_ffxivwiki,
}
source_name = {
    "jiki": "小鸡词典",
    "baidu": "百度百科",
    "nbnhhsh": "能不能好好说话",
    "ffxivwiki": "最终幻想14Wiki",
}


async def render_res(question: str, content: str, source: str) -> bytes:
    return await template_to_pic(
        template_path=template_path,
        template_name="what.html",
        pages={"viewport": {"width": 500, "height": 100}},
        templates={"what": {"question": question, "text": content, "from": source}},
    )


async def get_content(
    keyword: str, sources=["nbnhhsh", "ffxivwiki", "baidu"]
) -> Union[str, Message]:
    result = None
    msgs = await asyncio.gather(
        *[sources_func[s](keyword) for s in sources], return_exceptions=True
    )
    msgs = [
        (msg[0], msg[1], msg[2], idx)
        for idx, msg in enumerate(msgs)
        if isinstance(msg, Tuple) and msg[0]
    ]

    if msgs:
        if len(msgs) > 1:
            msgs = sorted(
                msgs,
                key=lambda m: fuzz.ratio(m[0].lower(), keyword.lower()),
                reverse=True,
            )
        result = MessageSegment.image(
            await render_res(
                f"{keyword} => {msgs[0][0]}" if keyword != msgs[0][0] else keyword,
                msgs[0][1],
                source_name[sources[msgs[0][3]]],
            )
        )
        if msgs[0][2]:
            result += f"\nURL:{msgs[0][2]}"
    return result
