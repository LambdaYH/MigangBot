import random
import asyncio
import datetime
from pathlib import Path

import aiohttp
from yarl import URL
from nonebot.log import logger
from nonebot.rule import to_me
from nonebot import on_fullmatch
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_htmlrender import template_to_pic
from nonebot.adapters.onebot.v11 import MessageSegment

from migang.core import DATA_PATH, TaskItem, broadcast

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

DAILYNEWS_PATH = DATA_PATH / "daily_news"
DAILYNEWS_PATH.mkdir(parents=True, exist_ok=True)
TEMPLATE_PATH = Path(__file__).parent / "templates"


async def get_zaobao() -> MessageSegment:
    import datetime

    weekday_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    try:
        from lunarcalendar import Lunar, Solar, Converter

        lunar_month_cn = [
            "",
            "正月",
            "二月",
            "三月",
            "四月",
            "五月",
            "六月",
            "七月",
            "八月",
            "九月",
            "十月",
            "冬月",
            "腊月",
        ]
        lunar_day_cn = [
            "",
            "初一",
            "初二",
            "初三",
            "初四",
            "初五",
            "初六",
            "初七",
            "初八",
            "初九",
            "初十",
            "十一",
            "十二",
            "十三",
            "十四",
            "十五",
            "十六",
            "十七",
            "十八",
            "十九",
            "二十",
            "廿一",
            "廿二",
            "廿三",
            "廿四",
            "廿五",
            "廿六",
            "廿七",
            "廿八",
            "廿九",
            "三十",
        ]
    except ImportError:
        Converter = None
        lunar_month_cn = []
        lunar_day_cn = []
    for i in range(3):
        try:
            async with aiohttp.ClientSession() as client:
                r = await client.get("https://60s-api.viki.moe/v2/60s", timeout=7)
                r = await r.json()
                if r["code"] == 200 and (data := r.get("data")):
                    news_list = data.get("news", [])
                    date = data.get("date", "")
                    tip = data.get("tip", "")
                    today = datetime.datetime.now()
                    weekday = weekday_map[today.weekday()]
                    # 获取农历
                    if Converter:
                        solar = Solar(today.year, today.month, today.day)
                        lunar = Converter.Solar2Lunar(solar)
                        lunar_month_day = (
                            f"{lunar_month_cn[lunar.month]}{lunar_day_cn[lunar.day]}"
                        )
                    else:
                        lunar_month_day = "农历信息缺失"
                    solar_year = f"{today.year}年"
                    solar_date = f"{today.month}月{today.day}日"
                    # 随机横幅渐变色
                    color_list = [
                        ("#1976d2", "#42a5f5"),
                        ("#ff9800", "#ffc107"),
                        ("#43cea2", "#185a9d"),
                        ("#ff5f6d", "#ffc371"),
                        ("#36d1c4", "#1e3c72"),
                        ("#f7971e", "#ffd200"),
                        ("#f953c6", "#b91d73"),
                        ("#4e54c8", "#8f94fb"),
                        ("#11998e", "#38ef7d"),
                        ("#fc5c7d", "#6a82fb"),
                    ]
                    c1, c2 = random.choice(color_list)
                    banner_color = f"linear-gradient(90deg, {c1} 0%, {c2} 100%)"
                    pic = await template_to_pic(
                        template_path=TEMPLATE_PATH,
                        template_name="dailynews.html",
                        templates={
                            "news_list": news_list,
                            "date": date,
                            "tip": tip,
                            "weekday": weekday,
                            "lunar_month_day": lunar_month_day,
                            "solar_year": solar_year,
                            "solar_date": solar_date,
                            "banner_color": banner_color,
                        },
                        pages={
                            "viewport": {"width": 800, "height": 600},
                        },
                    )
                    return MessageSegment.image(pic)
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
