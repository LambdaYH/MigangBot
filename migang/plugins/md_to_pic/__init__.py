import re

from nonebot import require
from nonebot import on_startswith
from nonebot.plugin import PluginMetadata
from nonebot.params import EventPlainText, Startswith
from nonebot.adapters.onebot.v11 import MessageSegment

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic

__plugin_meta__ = PluginMetadata(
    name="Markdown转图片",
    description="Markdown转图片",
    usage="""
usage：
    将markdown文本转图片
    指令：
        md2pic 文本
    说明：
        文本开头可带 [width=xxx]，指定生成的markdown图片宽度，默认为500
""".strip(),
    extra={
        "unique_name": "migang_md_to_pic",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_aliases__ = ["markdown转图片"]
__plugin_category__ = "一些工具"

md2pic = on_startswith(("md2pic", "markdown转图片"), priority=5, block=True)


@md2pic.handle()
async def _(plain_text: str = EventPlainText(), cmd: str = Startswith()):
    plain_text = plain_text.removeprefix(cmd).strip()
    if not plain_text:
        await md2pic.finish("请在指令后接上需要转换的文字哦~")
    width = 500
    if match := re.match(r"^\[width=(\d+)\]", plain_text):
        width = int(match.group(1))
        plain_text = plain_text.removeprefix(match.group(0)).strip()
    return await md2pic.send(
        MessageSegment.image(await md_to_pic(md=plain_text, width=width))
    )
