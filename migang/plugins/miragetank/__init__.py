"""
https://github.com/RafuiiChan/nonebot_plugin_miragetank
"""
from typing import List, Union

from nonebot import on_command
from nonebot.log import logger
from nonebot.typing import T_State
from nonebot.plugin import PluginMetadata
from nonebot.params import Arg, ArgStr, CommandArg
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.adapters.onebot.v11.helpers import (
    Numbers,
    HandleCancellation,
    extract_image_urls,
)

from .data_source import get_imgs, gray_car, seperate, color_car

__plugin_meta__ = PluginMetadata(
    name="幻影坦克",
    description="合成/分离幻影坦克图片",
    usage="""
合成/分离幻影坦克图片
注意：
    由于tx会很奇怪的偷偷修改图片格式，所以无法保证发送的图片或接受的图片符合预期，在测试下，大多数情况不正常。
    总之，聊胜于无
指令：
    合成幻影坦克
    分离幻影坦克 <图片> [亮度增强值]
可选参数：
    亮度增强值：取值建议 1~6，默认2（对应本插件合成的gray模式图，color模式图建议设置为5.5）
""".strip(),
)

priority = 27
__plugin_category__ = "一些工具"

mirage_tank = on_command("合成幻影坦克", priority=priority)
sep_miragetank = on_command("分离幻影坦克", priority=priority)


@mirage_tank.handle()
async def handle_first(
    event: MessageEvent, state: T_State, args: Message = CommandArg()
):
    mode = args.extract_plain_text().strip()
    img_urls = extract_image_urls(event.message)
    if mode:
        if mode not in ("gray", "color"):
            await mirage_tank.finish(f"模式仅可为 gray/color")
        state["gen_mode"] = mode
    if img_urls:
        state["gen_image_1"] = img_urls[0]
        if len(img_urls) >= 2:
            state["gen_image_2"] = img_urls[1]


@mirage_tank.got(
    key="gen_mode",
    prompt="请输入模式（gray/color），color模式下合成的里图是彩色的",
    parameterless=[HandleCancellation("已取消")],
)
async def _(state: T_State, mode: str = ArgStr("gen_mode")):
    if mode.strip() not in ("gray", "color"):
        await mirage_tank.reject("模式仅可为 gray/color")
    state["gen_mode"] = mode.strip()


@mirage_tank.got(
    key="gen_image_1",
    prompt="请发送第一张图片或同时发送两张",
    parameterless=[HandleCancellation("已取消")],
)
async def _(state: T_State, images: Union[Message, str] = Arg("gen_image_1")):
    if isinstance(images, Message):
        img_urls = extract_image_urls(images)
        if img_urls:
            state["gen_image_1"] = img_urls[0]
            if len(img_urls) >= 2:
                state["gen_image_2"] = img_urls[1]
        else:
            await mirage_tank.reject("请至少发送一张图片！")


@mirage_tank.got(
    key="gen_image_2",
    prompt="请发送第二张图片",
    parameterless=[HandleCancellation("已取消")],
)
async def _(state: T_State, images: Union[Message, str] = Arg("gen_image_2")):
    if isinstance(images, Message):
        img_urls = extract_image_urls(images)
        if img_urls:
            state["gen_image_2"] = img_urls[0]
        else:
            await mirage_tank.reject("请发送一张图片！")

    await mirage_tank.send("开始合成...")
    imgs = await get_imgs([state["gen_image_1"], state["gen_image_2"]])
    if len(imgs) < 2:
        await mirage_tank.finish("下载图片失败，过会再试吧")
    res = None
    if state["gen_mode"] == "gray":
        res = gray_car(*imgs)
    else:
        res = color_car(*imgs)
    if res:
        await mirage_tank.finish(MessageSegment.image(res))


# 分离幻影坦克
@sep_miragetank.handle()
async def _(
    event: MessageEvent,
    state: T_State,
    args: Message = CommandArg(),
    bright: List[float] = Numbers(),
):
    if event.reply:
        args.extend(event.reply.message)
    has_img = any(seg.type == "image" for seg in args)
    if has_img:
        state["miragetank_sep_img_url"] = args

    if bright:
        state["miragetank_sep_enhance_bright"] = bright[0]
    else:
        state["miragetank_sep_enhance_bright"] = 2


@sep_miragetank.got("miragetank_sep_img_url", prompt="请发送一张幻影坦克图片")
async def _(state: T_State, images: Message = Arg("miragetank_sep_img_url")):
    img_url = extract_image_urls(images)
    if not img_url:
        await sep_miragetank.finish("没有检测到图片，已结束")

    img = await get_imgs(img_url[:1])
    if not img:
        await sep_miragetank.finish("图片下载失败，待会再试吧")
    elif img[0].format != "PNG":
        await sep_miragetank.finish(f"图片格式为 {img[0].format}, 需要 PNG")
    logger.info("获取幻影坦克图片成功")
    await sep_miragetank.send("稍等，正在分离")
    try:
        outer, inner = seperate(
            img[0], bright_factor=state["miragetank_sep_enhance_bright"]
        )
    except Exception as e:
        logger.error(f"分离幻影坦克失败：{e}")
        await sep_miragetank.finish(f"分离失败：{e}", at_sender=True)
    await sep_miragetank.finish(
        MessageSegment.image(outer) + MessageSegment.image(inner), at_sender=True
    )
