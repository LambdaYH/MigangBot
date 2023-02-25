"""
https://github.com/A-kirami/nonebot-plugin-cartoon
"""
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.adapters.onebot.v11.helpers import extract_image_urls
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import Arg
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State

from .cartoon import cartonization

from migang.core import CDItem

__plugin_meta__ = PluginMetadata(
    name="图片卡通化",
    description="将三次元图片降维打击",
    usage="""
usage：
    将图片卡通（二次元）化
    依赖于：https://hylee-white-box-cartoonization.hf.space/
    指令：
        卡通化 [图片]

        或发送“卡通化”，而后参照提示

        或对带图片消息回复“卡通化”，请注意删除回复的前导@
""".strip(),
    extra={
        "unique_name": "migang_image_cartoonize",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_category__ = "好玩的"
__plugin_cd__ = CDItem(
    cd=1,
    hint="二向箔生产中，请稍后再来哦~",
)

cartoonize = on_command("卡通化", priority=8, block=True)


@cartoonize.handle()
async def _(event: MessageEvent, matcher: Matcher):
    message = reply.message if (reply := event.reply) else event.message
    if imgs := message["image"]:
        matcher.set_arg("imgs", imgs)


@cartoonize.got("imgs", prompt="请发送需要降维打击的图片")
async def _(state: T_State, imgs: Message = Arg()):
    urls = extract_image_urls(imgs)
    if not urls:
        await cartoonize.finish("似乎没找到图片信息呢，请带上图片重新发送吧~")
    state["urls"] = urls


@cartoonize.handle()
async def _(state: T_State):
    await cartoonize.send("正在准备二向箔, 请稍等...")
    try:
        image = await cartonization(state["urls"][0])
    except Exception as e:
        logger.opt(exception=e).warning("图像卡通化失败")
        await cartoonize.finish("二向箔发射失败, 请联系歌者或稍后重试", reply_message=True)
    await cartoonize.finish(MessageSegment.image(image), reply_message=True)
