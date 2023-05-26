"""
https://github.com/FloatTech/ZeroBot-Plugin
AGPL v3 协议开源
"""
from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message

from .data_source import rev_word

__plugin_meta__ = PluginMetadata(
    name="英文字符翻转",
    description="将英文字符翻转",
    usage="""
指令：
    字符翻转
示例：
    字符翻转 hello migang
""".strip(),
    extra={
        "unique_name": "migang_chrev",
        "example": "",
        "author": "migang",
        "version": "0.0.1",
    },
)
__plugin_category__ = "一些工具"

chrev = on_command("chrev", aliases={"字符翻转"}, priority=5)


@chrev.handle()
async def _(arg: Message = CommandArg()):
    word = arg.extract_plain_text()
    await chrev.send(rev_word(word))
