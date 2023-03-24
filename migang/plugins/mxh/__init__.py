import random
from pathlib import Path
from typing import Tuple
from nonebot import on_command
from nonebot.plugin import PluginMetadata
from nonebot.params import CommandArg, Command

from nonebot.adapters.onebot.v11 import Message
from migang.utils.file import async_load_data

__plugin_meta__ = PluginMetadata(
    name="梅溪湖cp短打",
    description="生成梅溪湖cp短打",
    usage=f"""
基于https://github.com/mxh-mini-apps/mxh-cp-stories
指令：
    梅溪湖 攻 受
    /mxh 攻 受
""".strip(),
    extra={
        "unique_name": "migang_mxh",
        "example": "",
        "author": "migang",
        "version": "0.0.1",
    },
)
__plugin_category__ = "好玩的"
__plugin_aliases__ = ["梅溪湖短打"]

story_path = Path(__file__).parent / "story.json"

mxh = on_command("/mxh", aliases={"梅溪湖"}, priority=5, block=True)


@mxh.handle()
async def _(cmds: Tuple[str, ...] = Command(), args: Message = CommandArg()):
    args = args.extract_plain_text().strip().split(" ")
    if len(args) != 2:
        await mxh.finish(f"参数错误：请按照【{cmds[0]} 攻 受】重新发送")
    stories = await async_load_data(story_path)
    story = random.choice(stories)
    story = story.replace("<攻>", args[0].strip()).replace("<受>", args[1].strip())
    await mxh.send(story)
