from nonebot.rule import to_me
from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler

from migang.core import DATA_PATH, TaskItem, broadcast

from .data_source import get_todayinhistory_image

__plugin_meta__ = PluginMetadata(
    name="历史上的今日",
    description="哔哩哔哩主题塔罗牌占卜",
    usage="""
usage：
    历史上的今日
    发送【开启历史上的今日推送】可每日推送，具体请查看群被动状态
    数据来源：百度百科https://baike.baidu.com/calendar/
    指令：
        查看历史上的今日：@Bot + 历史上的今日
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

__plugin_category__ = "订阅"
__plugin_task__ = TaskItem(task_name="today_in_history", name="历史上的今日推送")

todayinhistory = on_fullmatch("历史上的今日", priority=13, block=True, rule=to_me())

TIH_PATH = DATA_PATH / "today_in_history"
TIH_PATH.mkdir(parents=True, exist_ok=True)


@todayinhistory.handle()
async def _():
    await todayinhistory.finish(await get_todayinhistory_image(TIH_PATH))


@scheduler.scheduled_job("cron", hour="8", minute="32", jitter=50)
async def _():
    img = await get_todayinhistory_image(TIH_PATH)
    await broadcast("today_in_history", msg=img)
