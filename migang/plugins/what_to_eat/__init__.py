from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.plugin import on_regex, PluginMetadata
from nonebot.params import RegexGroup
from typing import Tuple, Any
from pathlib import Path
import random

__plugin_meta__ = PluginMetadata(
    name="今天吃什么",
    description="今天吃什么",
    usage="""
usage：
    简单用法：
        [今天吃什么] 看看今天吃啥
        [今天喝什么] 看看今天喝啥
    稍微复杂用法：
        直接看正则表达式吧：
            (今|明|后)?(天|日)?(早|中|晚)?(上|午|餐|饭|夜宵|宵夜)?(吃|喝)(什么|啥|点啥)
""".strip(),
    extra={
        "unique_name": "migang_what_to_eat",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)

what_eat_drink = on_regex(
    r"^(今|明|后)?(天|日)?(早|中|晚)?(上|午|餐|饭|夜宵|宵夜)?(吃|喝)(什么|啥|点啥)$", priority=5
)

IMAGE_PATH = Path(__file__).parent / "image"
img_eat_path = IMAGE_PATH / "eat_pic"
img_drink_path = IMAGE_PATH / "drink_pic"


@what_eat_drink.handle()
async def _(reg_group: Tuple[Any, ...] = RegexGroup()):
    path = img_eat_path if reg_group[4] == "吃" else img_drink_path
    img = random.choice(list(path.iterdir()))
    await what_eat_drink.send(
        f"{reg_group[0] or ''}{reg_group[1] or ''}{reg_group[2] or ''}{reg_group[3] or ''}去{reg_group[4]}{img.name.removesuffix(img.suffix)}吧~"
        + MessageSegment.image(img)
    )
