import random

import aiohttp
from nonebot import on_startswith
from nonebot.plugin import PluginMetadata
from nonebot.params import Startswith, EventPlainText

__plugin_meta__ = PluginMetadata(
    name="对联",
    description="生成对联",
    usage="""
指令：
    /duilian 上联
由https://ai.binwang.me/couplet提供
""".strip(),
    extra={
        "unique_name": "migang_duilian",
        "example": "",
        "author": "migang",
        "version": "0.0.1",
    },
)

duilian = on_startswith("/duilian", priority=5, block=True)


async def get_xialian(shanglian: str):
    async with aiohttp.ClientSession() as client:
        r = await client.get(
            f"https://seq2seq-couplet-model.rssbrain.com/v0.2/couplet/{shanglian}",
            timeout=15,
        )
        r = await r.json()
    if len(r["output"]) == 0:
        return ""
    return random.choice([i for i in r["output"] if i != ""])


@duilian.handle()
async def _(text: str = EventPlainText(), cmd: str = Startswith()):
    shanglian = text.removeprefix(cmd).strip()
    xialian = await get_xialian(shanglian)
    await duilian.send(f"上联：{shanglian}\n下联：{xialian}")
