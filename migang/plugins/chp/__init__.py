import asyncio
from pathlib import Path

import aiohttp
from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="彩虹屁",
    description="生成彩虹屁",
    usage="""
指令：
    /chp
""".strip(),
    extra={
        "unique_name": "migang_chp",
        "example": "",
        "author": "migang",
        "version": "0.0.1",
    },
)
__plugin_category__ = "好玩的"

story_path = Path(__file__).parent / "story.json"

chp = on_fullmatch("/chp", priority=5, block=True)


chp_url = "https://api.shadiao.pro/chp"


@chp.handle()
async def _():
    try:
        async with aiohttp.ClientSession() as client:
            r = await client.get(chp_url)
            data = await r.json()
            await chp.send(data["data"]["text"])
    except asyncio.TimeoutError:
        await chp.send("出错了...")
