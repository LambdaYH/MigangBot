import aiohttp
from nonebot.log import logger
from nonebot.rule import to_me
from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from migang.core import TaskItem, broadcast

__plugin_meta__ = PluginMetadata(
    name="摸鱼日历",
    description="每天早晨08点57分定时推送摸鱼日历",
    usage="""
usage：
    每日早报
    发送【开启摸鱼日历推送】可每日推送，具体请查看群被动状态
    指令：
        查看今日摸鱼日历：@Bot + 摸鱼日历
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_category__ = "订阅"
__plugin_task__ = TaskItem(task_name="moyu_calendar", name="摸鱼日历推送")


moyu_calendar = on_fullmatch("摸鱼日历", priority=26, block=True, rule=to_me())


async def get_calendar() -> Message:
    for i in range(3):
        try:
            async with aiohttp.ClientSession() as client:
                r = await client.get(
                    "https://api.j4u.ink/v1/store/other/proxy/remote/moyu.json",
                    timeout=7,
                )
                r = await r.json()
                if r["code"] == 200:
                    url = r["data"]["moyu_url"]
                    r = await client.head(url, allow_redirects=True)
                    return MessageSegment.image(str(r.url))
        except Exception as e:
            logger.warning(f"摸鱼日历获取失败，重试次数: {i}。{e}")
    return None


@scheduler.scheduled_job("cron", hour="8", minute="57", jitter=50)
async def _():
    moyu = await get_calendar()
    if not moyu:
        return
    await broadcast("moyu_calendar", moyu)


@moyu_calendar.handle()
async def _():
    moyu = await get_calendar()
    if not moyu:
        await moyu_calendar.finish("摸鱼日历获取失败", at_sender=True)
    await moyu_calendar.send(moyu)
