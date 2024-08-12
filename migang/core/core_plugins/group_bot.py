from nonebot.log import logger
from nonebot.rule import to_me
from nonebot.drivers import Driver
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Bot
from nonebot import require, get_driver, on_fullmatch

from migang.core.manager import group_bot_manager

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

__plugin_hidden__ = True
__plugin_always_on__ = True

driver: Driver = get_driver()

refresh = on_fullmatch(
    "刷新群机器人", rule=to_me(), permission=SUPERUSER, block=True, priority=1
)


@refresh.handle()
async def _():
    if await group_bot_manager.refreshAll():
        await refresh.send("群机器人刷新成功")
    else:
        await refresh.send("群机器人刷新失败")


@driver.on_bot_connect
async def _(bot: Bot):
    await group_bot_manager.add_bot(bot)


@driver.on_bot_disconnect
async def _(bot: Bot):
    group_bot_manager.del_bot(bot_id=int(bot.self_id))


@scheduler.scheduled_job("cron", minute=0, hour=0, day_of_week="mon")
async def _():
    """每周重新刷新下群"""
    await group_bot_manager.refreshAll()


@scheduler.scheduled_job("cron", minute=6)
async def _():
    """换班"""
    logger.info("换班时间到~")
    group_bot_manager.shuffle_group_bot()
