from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler
from nonebot.adapters.onebot.v11 import MessageSegment

from migang.core import TaskItem, broadcast

from ._data_source import build_alc_image

__plugin_meta__ = PluginMetadata(
    name="原神老黄历",
    description="",
    usage="""
usage：
    有时候也该迷信一回！特别是运气方面。
    群被动中可开启每日推送
    指令：
        原神黄历
""".strip(),
    extra={
        "unique_name": "migang_gushi",
        "example": "",
        "author": "HibiKier",
        "version": 0.1,
    },
)

__plugin_category__ = "原神相关"

__plugin_task__ = TaskItem(task_name="genshin_alc", name="原神黄历提醒")


almanac = on_fullmatch("原神黄历", priority=5, block=True)


@almanac.handle()
async def _():
    await almanac.send(MessageSegment.image(await build_alc_image()))


@scheduler.scheduled_job(
    "cron",
    hour=10,
    minute=25,
)
async def _():
    # 每日提醒
    alc_img = MessageSegment.image(await build_alc_image())
    if alc_img:
        await broadcast(task_name="genshin_alc", msg=alc_img)
