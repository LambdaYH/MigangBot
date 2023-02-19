import aiohttp
from fake_useragent import UserAgent
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="缩写查询",
    description="缩写查询",
    usage="""
usage：
    缩写 xxx
""".strip(),
    extra={
        "unique_name": "migang_suoxie",
        "example": "缩写 hhsh",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_category__ = "一些工具"

suoxie = on_command(cmd="缩写", aliases={"sx", "zy", "转义"}, priority=5, block=True)

url = f"https://lab.magiconch.com/api/nbnhhsh/guess/"


@suoxie.handle()
async def _(arg: Message = CommandArg()):
    try:
        episode = arg.extract_plain_text().strip()
        if not episode:
            await suoxie.finish("你想知道哪个拼音缩写的全称呢？请发送[缩写 xxx]查看哦", at_sender=True)
        body = {"text": episode}
        async with aiohttp.ClientSession() as client:
            r = await client.post(
                url=url,
                json=body,
                headers={
                    "content-type": "application/json",
                    "User-Agent": UserAgent(browsers=["chrome", "edge"]).random,
                },
                timeout=10,
            )
        data = (await r.json())[0]["trans"]
        msg = f"{episode}可能是【" + "，".join(data) + "】的缩写"
        await suoxie.send(msg, at_sender=True)
    except:
        await suoxie.send(
            f"没有发现缩写为{episode}的,可以前往https://lab.magiconch.com/nbnhhsh/ 添加词条",
            at_sender=True,
        )
