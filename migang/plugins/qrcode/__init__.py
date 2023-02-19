from io import BytesIO

import aiohttp
from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State
from PIL import Image, ImageEnhance
from pyzbar import pyzbar

__plugin_meta__ = PluginMetadata(
    name="二维码转链接",
    description="将二维码图片转化为链接发出",
    usage="""
usage：
    将二维码图片转换成链接(最多同时识别3张，防止刷屏)
    指令:
        二维码 [图片]
""".strip(),
    extra={
        "unique_name": "migang_translate",
        "example": "翻译 hello",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_aliases__ = ["二维码", "二维码识别"]
__plugin_category__ = "一些工具"

qrcode = on_command(cmd="二维码", aliases={"qrcode"}, priority=5, block=True)


def image_enhance(im):
    if im.format == "GIF":
        im = im.convert("RGB")
    eim = ImageEnhance.Brightness(im).enhance(2.0)

    return im, eim


def decoded_list(barcodes):
    result = set()
    for code in barcodes:
        result.add(code.data.decode("utf-8"))
    return result


def decode(file):
    if isinstance(file, bytes):
        img = Image.open(BytesIO(file))
        im, eim = image_enhance(img)
        for barcode in decoded_list(pyzbar.decode(im) + pyzbar.decode(eim)):
            yield barcode
    else:
        with file.open("rb") as f:
            img = Image.open(f)
            im, eim = image_enhance(img)
            for barcode in decoded_list(pyzbar.decode(im) + pyzbar.decode(eim)):
                yield barcode


@qrcode.handle()
async def _(
    event: MessageEvent,
    state: T_State,
):
    msg = event.reply.message if event.reply else event.message
    imgs = [seg.data["url"] for seg in msg["image"]]
    if imgs:
        state["image"] = imgs


@qrcode.got("image", prompt="请发送需要识别的二维码图片")
async def _(bot: Bot, event, state: T_State):
    if isinstance(state["image"], Message):
        imgs = [seg.data["url"] for seg in state["image"]]
        if not imgs:
            await qrcode.finish("请发送二维码图片哦~", at_sender=True)
        image_url = imgs
    else:
        image_url = state["image"]

    msg_list = []

    async with aiohttp.ClientSession() as client:
        for i in image_url:
            img = await client.get(i, timeout=15)
            urls = "\n".join(decode(await img.read()))
            if not urls:
                continue
            msg_list.append(
                {
                    "type": "node",
                    "data": {
                        "name": list(bot.config.nickname)[0],
                        "uin": f"{bot.self_id}",
                        "content": urls,
                    },
                }
            )
    if not msg_list:
        await qrcode.finish("未检测到二维码", at_sender=True)
    if len(msg_list) == 1:
        await qrcode.finish(
            MessageSegment.reply(event.message_id) + msg_list[0]["data"]["content"]
        )
    await qrcode.send(MessageSegment.reply(event.message_id) + "各二维码对应的链接如下")
    if isinstance(event, GroupMessageEvent):
        await bot.send_forward_msg(group_id=event.group_id, messages=msg_list)
    else:
        await bot.send_forward_msg(user_id=event.user_id, messages=msg_list)
