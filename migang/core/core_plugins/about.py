from nonebot.rule import to_me
from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="关于_",
    description="",
    usage="""
usage：
    指令：
        关于
""".strip(),
    extra={
        "unique_name": "migang_about",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)

about = on_fullmatch("关于", rule=to_me(), priority=1, block=False)


@about.handle()
async def _():
    await about.send(
        """
基于NoneBot2的米缸Bot
开源地址：https://github.com/LambdaYH/MigangBot
""".strip()
    )
