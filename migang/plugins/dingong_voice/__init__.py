import random
from pathlib import Path

from nonebot.rule import to_me
from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import MessageSegment

from migang.core import CDItem

__plugin_meta__ = PluginMetadata(
    name="骂我",
    description="请狠狠的骂我一次！",
    usage="""
usage：
    多骂我一点，球球了
    指令：
        骂我
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_cd__ = CDItem(3, hint="喝杯水先...")

dg_voice = on_fullmatch("骂我", rule=to_me(), priority=5, block=True)
RECORD_PATH = Path(__file__).parent / "res"


@dg_voice.handle()
async def _():
    voice = random.choice(list(RECORD_PATH.iterdir()))
    await dg_voice.send(MessageSegment.record(voice))
