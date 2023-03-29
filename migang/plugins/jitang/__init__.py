import asyncio

import aiohttp
from nonebot import on_regex
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="鸡汤",
    description="生成发病小作文",
    usage="""
usage：
    不喝点什么感觉有点不舒服
    指令：
        鸡汤
""".strip(),
    extra={
        "unique_name": "migang_jitang",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)

jitang = on_regex("^毒?鸡汤$", priority=5, block=True)


jitang_url = "https://api.shadiao.pro/du"


@jitang.handle()
async def _():
    try:
        async with aiohttp.ClientSession() as client:
            r = await client.get(jitang_url)
            data = await r.json()
            await jitang.send(data["data"]["text"])
    except asyncio.TimeoutError:
        await jitang.send("鸡汤煮坏掉了...")
