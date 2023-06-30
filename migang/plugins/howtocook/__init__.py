import asyncio

from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata
from nonebot.params import CommandArg, EventPlainText
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot import require, on_command, on_endswith, on_fullmatch

from migang.core import post_init_manager

from .data_source import MENU_FILE, IMAGE_PATH, MENU_IMAGE, update_all

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

__plugin_meta__ = PluginMetadata(
    name="做饭指南",
    description="做饭指南，看菜谱",
    usage="""
https://github.com/Anduin2017/HowToCook
指令：
    菜谱 xxx
    翻开菜谱
    xxx怎么做
示例：
    菜谱 蛋炒饭
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

__plugin_category__ = "一些工具"

menu = set()


@post_init_manager
async def _():
    asyncio.create_task(update_all(menu=menu, need_update_menu=not MENU_FILE.exists()))


@scheduler.scheduled_job("cron", minute=6, hour=12)
async def _():
    await update_all(menu=menu, need_update_menu=True)


howtocook = on_command("菜谱", priority=5, block=True)
howtocook_nlp = on_endswith("怎么做", priority=100, block=False)
open_menu = on_fullmatch("翻开菜谱", priority=5, block=True)


@howtocook.handle()
async def _(arg: Message = CommandArg()):
    dish = arg.extract_plain_text()
    if dish not in menu:
        await howtocook.finish(
            f"未找到{dish}的制作方法，请查看菜谱哦" + MessageSegment.image(MENU_IMAGE)
        )
    await howtocook.send(MessageSegment.image(IMAGE_PATH / f"{dish}.png"))


@howtocook_nlp.handle()
async def _(matcher: Matcher, plain_text: str = EventPlainText()):
    dish = plain_text[:-3].strip()
    if dish in menu:
        matcher.stop_propagation()
        await howtocook_nlp.send(MessageSegment.image(IMAGE_PATH / f"{dish}.png"))


@open_menu.handle()
async def _():
    await open_menu.send(MessageSegment.image(MENU_IMAGE))
