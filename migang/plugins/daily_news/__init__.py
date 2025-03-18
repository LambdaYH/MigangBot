import asyncio

import aiohttp
from yarl import URL
from nonebot.log import logger
from nonebot.rule import to_me
from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler
from nonebot.adapters.onebot.v11 import MessageSegment

from migang.core import TaskItem, broadcast

__plugin_meta__ = PluginMetadata(
    name="今日早报",
    description="每天早晨09点09分定时推送今日早报",
    usage="""
usage：
    每日早报
    发送【开启每日早报】可每日推送，具体请查看群被动状态
    可设定每天早晨09点09分定时推送
    指令：
        查看今日早报：@Bot + 今日早报
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

__plugin_category__ = "订阅"


__plugin_task__ = TaskItem(
    task_name="daily_news", name="每日早报", description="每天早晨09点09分定时推送今日早报"
)


dailynews = on_fullmatch("今日早报", priority=13, block=True, rule=to_me())


async def get_zaobao() -> MessageSegment:
    for i in range(3):
        try:
            async with aiohttp.ClientSession() as client:
                r = await client.get("https://60s-api.viki.moe/v2/60s", timeout=7)
                r = await r.json()
                if r["code"] == 200 and (data := r.get("data")):
                    url = data["image"]
                    img = await client.get(
                        url,
                        headers={"referer": f"{URL(url).scheme}://{URL(url).host}/"},
                    )
                    if img.status == 200:
                        return MessageSegment.image(await img.read())
        except Exception as e:
            logger.warning(f"今日早报获取失败，重试次数: {i}。{e}")
            await asyncio.sleep(0.2)
    return None


@scheduler.scheduled_job("cron", hour="9", minute="30", jitter=50)
async def _():
    zaobao = await get_zaobao()
    if not zaobao:
        return
    await broadcast(task_name="daily_news", msg=zaobao)


@dailynews.handle()
async def _():
    zaobao = await get_zaobao()
    if not zaobao:
        await dailynews.finish("今日早报获取失败", at_sender=True)
    await dailynews.send(zaobao)
