from io import BytesIO
from typing import Annotated

import qrcode
from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment

__plugin_meta__ = PluginMetadata(
    name="生成二维码",
    description="生成二维码",
    usage="""
usage：
    将文字转换成二维码
    指令:
        生成二维码
""".strip(),
    extra={
        "unique_name": "migang_make_qrcode",
        "example": "生成二维码",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_category__ = "一些工具"

make_qrcode = on_command(cmd="生成二维码", priority=5, block=True)


@make_qrcode.handle()
async def _(event: MessageEvent, args: Annotated[Message, CommandArg()]):
    text = args.extract_plain_text()
    if not text:
        await make_qrcode.finish("用于转换二维码的文字不能为空")
    try:
        img = qrcode.make(text)
    except qrcode.DataOverflowError:
        await make_qrcode.finish("用于转换二维码的文字似乎太长了...")
    with BytesIO() as buf:
        img.save(buf)
        await make_qrcode.send(
            MessageSegment.reply(event.message_id) + MessageSegment.image(buf)
        )
