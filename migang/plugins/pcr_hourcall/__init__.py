"""HoshinoBot来的
"""
from datetime import datetime

from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler

from migang.core import TaskItem, broadcast

from .data import HOUR_CALLS, HOUR_CALLS_ON

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="pcr风格整点报时_",
    description="pcr风格整点报时",
    usage="",
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_task__ = TaskItem(task_name="pcr_hourcall", name="pcr风格整点报时")


def get_hour_call():
    """挑出一组时报，每日更换，一日之内保持相同"""
    now = datetime.now()
    hc_groups = HOUR_CALLS_ON
    g = hc_groups[now.day % len(hc_groups)]
    return HOUR_CALLS[g]


@scheduler.scheduled_job("cron", hour="*")
async def hour_call():
    now = datetime.now()
    if 2 <= now.hour <= 4:
        return  # 宵禁 免打扰
    msg = get_hour_call()[now.hour]
    await broadcast("pcr_hourcall", msg=msg)
