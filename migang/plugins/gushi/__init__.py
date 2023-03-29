import asyncio

import aiohttp
from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="古诗",
    description="为什么突然文艺起来了！",
    usage="""
usage：
    平白无故念首诗
    指令：
        念诗/来首诗/念首诗
""".strip(),
    extra={
        "unique_name": "migang_gushi",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)


gushi = on_fullmatch(("念诗", "来首诗", "念首诗"), priority=5, block=True)


gushi_url = "https://v1.jinrishici.com/all"


@gushi.handle()
async def _():
    try:
        async with aiohttp.ClientSession() as client:
            r = await client.get(gushi_url)
            data = await r.json()
            await gushi.send(
                f"{data['content']}\n\t——{data['author']}《{data['origin']}》"
            )
    except asyncio.TimeoutError:
        await gushi.send("获取古诗超时了...")
