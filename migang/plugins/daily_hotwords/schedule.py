from datetime import time
from typing import Dict, Tuple, Optional

from nonebot.log import logger
import nonebot_plugin_saa as saa
from apscheduler.job import Job
from nonebot_plugin_apscheduler import scheduler
from sqlalchemy import JSON, Select, cast, select
from nonebot_plugin_datastore.db import get_engine
from nonebot_plugin_datastore import create_session
from nonebot_plugin_cesaa import get_messages_plain_text
from nonebot_plugin_wordcloud.utils import (
    get_datetime_now_with_timezone,
    get_time_with_scheduler_timezone,
)

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

from nonebot_plugin_wordcloud.config import plugin_config
from nonebot_plugin_wordcloud.utils import get_mask_key, time_astimezone

from .model import Schedule
from .data_source import get_wordcloud_and_hot_words

saa.enable_auto_select_bot()


class Scheduler:
    def __init__(self):
        # 默认定时任务的 key 为 default
        # 其他则为 ISO 8601 格式的时间字符串
        self.schedules: Dict[str, Job] = {}

        # 转换到 APScheduler 的时区
        scheduler_time = get_time_with_scheduler_timezone(
            plugin_config.wordcloud_default_schedule_time
        )
        # 添加默认定时任务
        self.schedules["default"] = scheduler.add_job(
            self.run_task,
            "cron",
            hour=scheduler_time.hour,
            minute=scheduler_time.minute,
            second=scheduler_time.second,
        )

    async def update(self):
        """更新定时任务"""
        async with create_session() as session:
            statement = (
                select(Schedule.time)
                .group_by(Schedule.time)
                .where(Schedule.time != None)
            )
            schedule_times = await session.scalars(statement)
            for schedule_time in schedule_times:
                assert schedule_time is not None
                time_str = schedule_time.isoformat()
                if time_str not in self.schedules:
                    # 转换到 APScheduler 的时区，因为数据库中的时间是 UTC 时间
                    scheduler_time = get_time_with_scheduler_timezone(
                        schedule_time.replace(tzinfo=ZoneInfo("UTC"))
                    )
                    self.schedules[time_str] = scheduler.add_job(
                        self.run_task,
                        "cron",
                        hour=scheduler_time.hour,
                        minute=scheduler_time.minute,
                        second=scheduler_time.second,
                        args=(schedule_time,),
                    )
                    logger.debug(f"已添加每日热词定时发送任务，发送时间：{time_str} UTC")

    async def run_task(self, time: Optional[time] = None):
        """执行定时任务

        时间为 UTC 时间，并且没有时区信息
        如果没有传入时间，则执行默认定时任务
        """
        async with create_session() as session:
            statement = select(Schedule).where(Schedule.time == time)
            results = await session.scalars(statement)
            schedules = results.all()
            # 如果该时间没有需要执行的定时任务，且不是默认任务则从任务列表中删除该任务
            if time and not schedules:
                self.schedules.pop(time.isoformat()).remove()
                return
            logger.info(f"开始发送每日热词，时间为 {time or '默认时间'}")
            for schedule in schedules:
                target = schedule.saa_target
                dt = get_datetime_now_with_timezone()
                start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                stop = dt
                messages = await get_messages_plain_text(
                    target=target,
                    types=["message"],
                    time_start=start,
                    time_stop=stop,
                    exclude_id1s=plugin_config.wordcloud_exclude_user_ids,
                )
                mask_key = get_mask_key(target)
                words_image = await get_wordcloud_and_hot_words(messages, mask_key)
                if not words_image:
                    await saa.Text("今天没有足够的数据生成热词").send_to(target)
                    continue

                msg_builder = saa.MessageFactory[
                    saa.Text("欢迎收看由本日聊天信息生成的今日热词："),
                    saa.Text("\n".join(words_image[0])),
                    saa.Image(words_image[1]),
                ]
                await msg_builder.send_to(target)

    async def get_schedule(self, target: saa.PlatformTarget) -> Optional[time]:
        """获取定时任务时间"""
        async with create_session() as session:
            statement = self.select_target_statement(target)
            results = await session.scalars(statement)
            if schedule := results.one_or_none():
                if schedule.time:
                    # 将时间转换为本地时间
                    return time_astimezone(
                        schedule.time.replace(tzinfo=ZoneInfo("UTC"))
                    )
                else:
                    return plugin_config.wordcloud_default_schedule_time

    async def add_schedule(
        self, target: saa.PlatformTarget, *, time: Optional[time] = None
    ):
        """添加定时任务

        时间需要带时区信息
        """
        # 将时间转换为 UTC 时间
        if time:
            time = time_astimezone(time, ZoneInfo("UTC"))

        async with create_session() as session:
            statement = self.select_target_statement(target)
            results = await session.scalars(statement)
            if schedule := results.one_or_none():
                schedule.time = time
            else:
                schedule = Schedule(time=time, target=target.dict())
                session.add(schedule)
            await session.commit()
        await self.update()

    async def remove_schedule(self, target: saa.PlatformTarget):
        """删除定时任务"""
        async with create_session() as session:
            statement = self.select_target_statement(target)
            results = await session.scalars(statement)
            if schedule := results.one_or_none():
                await session.delete(schedule)
                await session.commit()

    @staticmethod
    def select_target_statement(target: saa.PlatformTarget) -> Select[Tuple[Schedule]]:
        """获取查询目标的语句

        MySQL 需要手动将 JSON 类型的字段转换为 JSON 类型
        """
        if get_engine().dialect.name == "mysql":
            return select(Schedule).where(Schedule.target == cast(target.dict(), JSON))
        return select(Schedule).where(Schedule.target == target.dict())


schedule_service = Scheduler()
