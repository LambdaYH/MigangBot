import aiohttp
from nonebot.rule import to_me
from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="一言二次元语录",
    description="解析群聊消息中的各类链接",
    usage="""
usage：
    一言二次元语录
    指令（需@）：
        二次元语录
""".strip(),
    extra={
        "unique_name": "migang_quotation",
        "example": "",
        "author": "HibiKier",
        "version": 0.1,
    },
)

quotations = on_fullmatch("二次元语录", priority=5, block=True, rule=to_me())

url = "https://international.v1.hitokoto.cn/?c=a"


@quotations.handle()
async def _():
    async with aiohttp.ClientSession() as client:
        data = await (await client.get(url, timeout=5)).json()
    result = f'{data["hitokoto"]}\t——{data["from"]}'
    await quotations.send(result)
