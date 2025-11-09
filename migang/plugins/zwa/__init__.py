import random
from time import time
from pathlib import Path

import aiohttp
from nonebot import get_bot
from nonebot.log import logger
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler
from nonebot.adapters.onebot.v11 import MessageSegment

from migang.core import TaskItem, broadcast

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="早晚安_",
    description="发送早晚安问候",
    usage="""
usage：
    发送早晚安问候，群被动里去设置
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_category__ = "群功能"
__plugin_task__ = (
    TaskItem(task_name="good_morning", name="早安"),
    TaskItem(task_name="good_night", name="晚安"),
)

IMAGE_PATH = Path(__file__).parent / "image"

MORNING = (
    "早上好呀",
    "大家早上好！",
    "早上好~",
    "各位早上好！",
)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
    "Accept-Encoding": "gzip, deflate",
}


async def get_moring_message() -> str:
    """获得早上问好

    日期不同，不同的问候语
    通过 [免费节假日 API](https://timor.tech/api/holiday/)
    """
    for i in range(3):
        try:
            # 获得不同的问候语
            async with aiohttp.ClientSession() as client:
                r = await client.get(
                    f"https://timor.tech/api/holiday/tts?t={int(time())}",
                    timeout=7,
                    headers=_HEADERS,
                )
                rjson = await r.json()
            if rjson["code"] == 0:
                return f"{random.choice(MORNING)}\n{rjson['tts']}"
        except Exception as e:
            logger.warning(f"获取问候语失败{i}/3：{e}")

    return random.choice(MORNING)


# 早上好
@scheduler.scheduled_job("cron", hour=8, minute=8, jitter=300)
async def _():
    await broadcast(
        task_name="good_morning",
        msg=await get_moring_message() + MessageSegment.image(IMAGE_PATH / "zaoan.gif"),
    )


@scheduler.scheduled_job("cron", hour=23, minute=30, jitter=300)
async def _():
    bot = get_bot()
    await broadcast(
        task_name="good_night",
        msg=f"{list(bot.config.nickname)[0]}要睡觉了，你们也要早点睡呀"
        + MessageSegment.image(IMAGE_PATH / "wanan.jpg"),
    )
