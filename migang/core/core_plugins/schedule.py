"""核心定时任务
"""

from nonebot import require
from nonebot_plugin_apscheduler import scheduler

from migang.core import CountPeriod
from migang.core.manager import count_manager, save

require("nonebot_plugin_apscheduler")


# 重置插件限制
@scheduler.scheduled_job("cron", minute=0)
async def _():
    count_manager.reset(CountPeriod.hour)


@scheduler.scheduled_job("cron", minute=0, hour=0)
async def _():
    count_manager.reset(CountPeriod.day)


@scheduler.scheduled_job("cron", minute=0, hour=0, day_of_week="mon")
async def _():
    count_manager.reset(CountPeriod.week)


@scheduler.scheduled_job("cron", minute=0, hour=0, day=1)
async def _():
    count_manager.reset(CountPeriod.month)


@scheduler.scheduled_job("cron", minute=0, hour=0, day=1, month=1)
async def _():
    count_manager.reset(CountPeriod.year)


# 自动保存
@scheduler.scheduled_job("interval", minutes=15, jitter=120)
async def _():
    await save()
