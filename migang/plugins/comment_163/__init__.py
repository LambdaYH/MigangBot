from nonebot import on_fullmatch
import aiohttp
import asyncio
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="网易云热评",
    description="生成发病小作文",
    usage="""
usage：
    到点了，还是防不了下塔
    指令：
        网易云热评
""".strip(),
    extra={
        "unique_name": "migang_alapi_comments_163",
        "example": "",
        "author": "HibiKier",
        "version": 0.1,
    },
)

comment_163 = on_fullmatch("网易云热评", priority=5, block=True)


comments_163_url = "https://keai.icu/apiwyy/api"


@comment_163.handle()
async def _():
    try:
        async with aiohttp.ClientSession() as client:
            r = await client.get(comments_163_url)
            data = await r.json(content_type=None)
            await comment_163.send(f"{data['content']}\n\t——《{data['music']}》")
    except asyncio.TimeoutError:
        await comment_163.send("获取网易云热评超时了...")
