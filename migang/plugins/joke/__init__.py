"""
https://github.com/SAGIRI-kawaii/sagiri-bot/tree/Ariadne-v4/modules/self_contained/joke
"""
import random
from pathlib import Path
from typing import Tuple, Annotated

from nonebot import on_regex
from nonebot.params import RegexGroup
from nonebot.plugin import PluginMetadata

from migang.utils.file import async_load_data

__plugin_meta__ = PluginMetadata(
    name="笑话",
    description="生成笑话",
    usage="""
usage：
    指令：
        来点笑话
        来点(关键词/法国/苏联/美国)笑话
    示例：
        来点苏联笑话
        来自xx笑话
    说明：
        关键词不超过五个字
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

joke = on_regex(r"^来点([\S\s]{0,5})笑话$", priority=5, block=True)

joke_path = Path(__file__).parent / "jokes.json"


@joke.handle()
async def _(reg_group: Annotated[Tuple, RegexGroup()]):
    data = await async_load_data(joke_path)
    if reg_group[0] not in data:
        msg = random.choice(data["jokes"]).format(name=reg_group[0])
    else:
        msg = random.choice(data[reg_group[0]])
    await joke.send(msg)
