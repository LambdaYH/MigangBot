import random
from pathlib import Path
from datetime import datetime

import anyio
import ujson as json
from nonebot_plugin_htmlrender import template_to_pic
from nonebot.adapters.onebot.v11 import MessageSegment

template_path = Path(__file__).parent / "templates"


async def get_data():
    async with await anyio.open_file(
        Path(__file__).parent / "data.json", "r", encoding="utf8"
    ) as f:
        words = json.loads(await f.read())
    return random.choice(words)


async def get_fabing(target, author):
    illness = await get_data()
    text = illness["text"]
    person = illness["person"]
    text = text.replace(person, target)
    image = await template_to_pic(
        template_path=template_path,
        template_name="fabing.html",
        templates={
            "article": {
                "author": author,
                "text": text,
                "like": random.randint(0, 9999),
                "quote": random.randint(0, 9999),
                "time": datetime.today().date(),
            }
        },
        pages={
            "viewport": {"width": 500, "height": 100},
        },
    )
    return MessageSegment.image(image)
