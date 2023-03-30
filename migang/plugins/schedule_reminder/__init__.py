from typing import Union
from datetime import datetime

from nonebot.log import logger
from pil_utils import text2image
from nonebot.typing import T_State
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError
from nonebot.params import Arg, ArgStr, Depends, CommandArg
from nonebot import get_bot, require, on_command, on_fullmatch
from nonebot.adapters.onebot.v11 import (
    GROUP_ADMIN,
    GROUP_OWNER,
    Bot,
    Message,
    MessageEvent,
    MessageSegment,
    GroupMessageEvent,
    PrivateMessageEvent,
)

require("nonebot_plugin_datastore")
from sqlalchemy import select
from nonebot_plugin_datastore.db import post_db_init
from sqlalchemy.ext.asyncio.session import AsyncSession
from nonebot_plugin_datastore import get_session, create_session

from migang.core import DATA_PATH
from migang.utils.image import pic_to_bytes
from migang.utils.file import async_load_data

from .model import Schedule
from .data_source import (
    cron_parse,
    date_parse,
    interval_parse,
    serialize_message,
    deserialize_message,
)

__plugin_meta__ = PluginMetadata(
    name="简易自定义定时消息",
    description="简易自定义定时消息",
    usage="""
usage：
    [添加定时任务 任务类型] 来添加
    [删除定时任务 任务id] 来删除
    [查看定时任务 任务id] 来查看特定定时任务
    [查看定时任务] 来查看当前用户所有定时任务

    [查看群定时任务] 查看当前群聊中的所有定时任务，仅群管理员可使用
    [删除群定时任务 任务id] 删除当前群聊中的定时任务，仅群管理员可使用

    任务类型有
    interval: 间隔
    date: 特定日期
    cron: cron格式

    具体参考提示来进行
    可发送[定时任务帮助]查看例子
""".strip(),
    extra={
        "unique_name": "migang_schedule_reminder",
        "example": "",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_category__ = "群功能"


async def do_job(group_id: int, user_id: int, msg: str, id_: str, once=False):
    bot = get_bot()
    try:
        if group_id:
            await bot.send_group_msg(
                group_id=group_id,
                message=msg,
            )
        elif user_id:
            await bot.send_private_msg(
                user_id=user_id,
                message=msg,
            )
        else:
            try:
                scheduler.remove_job(id_)
                logger.warning(f"无效定时任务[{id_}]已被自动移除")
            except JobLookupError:
                pass
    except:
        logger.warning(f"定时任务[{id_}]发送失败")

    if once:
        async with create_session() as session:
            schedule = await session.scalar(
                select(Schedule).where(Schedule.id == int(id_))
            )
            await session.delete(schedule)
            await session.commit()


@post_db_init
async def _():
    old_schedule_tasks = DATA_PATH / "schedule_reminder" / "schedule_tasks.json"
    async with create_session() as session:
        if old_schedule_tasks.exists():
            data = await async_load_data(old_schedule_tasks)
            for user, jobs in data.items():
                for job in jobs.values():
                    schedule = Schedule(
                        user_id=int(user),
                        group_id=job["gid"],
                        type=job["type"],
                        content=await serialize_message(Message(job["msg"])),
                        param={},
                    )
                    if job["type"] == "interval":
                        interval_type = job["intervalType"]
                        interval = job["interval"]
                        schedule.param["trigger"] = "interval"
                        if interval_type == "m":
                            schedule.param["minutes"] = interval
                        elif interval_type == "h":
                            schedule.param["hours"] = interval
                        elif interval_type == "d":
                            schedule.param["days"] = interval
                    elif job["type"] == "cron":
                        schedule.param["cron"] = job["cron"]
                    elif job["type"] == "date":
                        try:
                            time = datetime.strptime(
                                job["time"], "%Y-%m-%d %H:%M:%S.%f"
                            )
                        except:
                            time = datetime.strptime(job["time"], "%Y-%m-%d %H:%M:%S")
                        schedule.param["run_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    session.add(schedule)
            old_schedule_tasks.rename(
                old_schedule_tasks.parent / "schedule_tasks.json.old"
            )
            await session.commit()
        jobs = await session.scalars(select(Schedule))
        for job in jobs:
            if job.type == "cron":
                scheduler.add_job(
                    do_job,
                    CronTrigger.from_crontab(job.param["cron"]),
                    id=str(job.id),
                    args=[
                        job.group_id,
                        job.user_id,
                        deserialize_message(job.content),
                        str(job.id),
                    ],
                )
            elif job.type == "interval":
                scheduler.add_job(
                    do_job,
                    **job.param,
                    id=str(job.id),
                    args=[
                        job.group_id,
                        job.user_id,
                        deserialize_message(job.content),
                        str(job.id),
                    ],
                )
            elif job.type == "date":
                time = datetime.strptime(job.param["run_date"], "%Y-%m-%d %H:%M:%S")
                scheduler.add_job(
                    do_job,
                    "date",
                    run_date=time,
                    id=str(job.id),
                    args=[
                        job.group_id,
                        job.user_id,
                        deserialize_message(job.content),
                        str(job.id),
                        True,
                    ],
                )
            logger.info(f"载入定时任务[{job.id}]成功")


TYPELIST = {
    # interval
    "interval": "interval",
    "间隔": "interval",
    # date
    "date": "date",
    "日期": "date",
    "单次": "date",
    "一次": "date",
    "不重复": "date",
    # cron
    "cron": "cron",
    "定时": "cron",
}

TIMEEXAMPLE = {
    "interval": "m:2(表示每2分钟),h:2(表示每2小时),d:2(表示每两天)",
    "date": "2022年1月1日(2022年一月一日触发),2天后(2天后触发),明天1点30分(明天1点30分触发)",
    "cron": "https://crontab.guru/",
}


add_task = on_command("添加定时任务", aliases={"/定时任务"}, priority=5, block=True)
del_task = on_command("删除定时任务", priority=5, block=True)
show_task = on_command("查看定时任务", priority=5, block=True)
help_task = on_fullmatch("定时任务帮助", priority=5, block=True)

show_group_task = on_fullmatch(
    "查看群定时任务", priority=5, block=True, permission=GROUP_OWNER | GROUP_ADMIN
)
del_group_task = on_command(
    "删除群定时任务", priority=5, block=True, permission=GROUP_OWNER | GROUP_ADMIN
)


@add_task.handle()
async def _(event: MessageEvent, state: T_State, arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip()
    if args:
        state["job_type"] = args
    user_id = event.user_id
    state["user_id"] = user_id

    group_id = None
    if event.message_type == "group":
        if event.sender.role == "member":
            await add_task.finish("群聊中仅允许管理员添加定时任务！")
        group_id = event.group_id
    state["group_id"] = group_id


@add_task.got(
    "job_type",
    prompt="请发送所选择的定时任务种类：\ninterval: 间隔\ndate: 特定日期\ncron: cron格式\n输入冒号前的英文单词",
)
async def _(state: T_State, job_type: str = ArgStr("job_type")):
    type_ = -1
    if TYPELIST.get(job_type):
        type_ = TYPELIST[job_type]
    else:
        await add_task.finish("定时任务类型设置错误，仅支持[date, interval, cron]，具体可发送[定时任务帮助]查看")
    state["type"] = type_


@add_task.got("msg_to_sent", prompt="请输入定时任务触发时所要发送的消息")
async def _(state: T_State, msg_to_sent: Message = Arg("msg_to_sent")):
    if not msg_to_sent:
        await add_task.finish("定时任务设置错误，消息不得为空")
    msg_to_sent = await serialize_message(msg_to_sent)
    state["msg_to_sent"] = msg_to_sent
    await add_task.send(
        f"当前定时任务类型为{state['job_type']}, 参考[{TIMEEXAMPLE[str(state['type'])]}]"
    )


@add_task.got(
    "time_setting",
    prompt=f"请根据您所设定的类型输入时间参数",
)
async def _(state: T_State, time_setting: str = ArgStr("time_setting")):
    user_id = state["user_id"]
    group_id = state["group_id"]
    msg_to_sent = state["msg_to_sent"]
    type_ = state["type"]
    param = {}
    if type_ == "interval":
        check, t, interval = interval_parse(time_setting)
        if not check:
            await add_task.finish(t)
        param["trigger"] = "interval"
        if t == "m":
            param["minutes"] = interval
        elif t == "d":
            param["days"] = interval
        elif t == "h":
            param["hours"] = interval
    elif type_ == "date":
        check, time = date_parse(time_setting)
        if not check:
            await add_task.finish(f"参数错误，请参考{TIMEEXAMPLE[str(type)]}，或发送[定时任务帮助]查看")
        if time <= datetime.now():
            await add_task.finish(f"请不要设置过去的时间哦，设定的时间{time}，当前时间{datetime.now()}")
        param["run_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
    elif type_ == "cron":
        check, _, _, _ = cron_parse(time_setting)
        if not check:
            await add_task.finish(f"参数错误，请参考{TIMEEXAMPLE[str(type)]}，或发送[定时任务帮助]查看")
        param["cron"] = time_setting

    async with create_session() as session:
        job = Schedule(
            user_id=user_id,
            group_id=group_id,
            type=type_,
            param=param,
            content=msg_to_sent,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        if job.type == "cron":
            scheduler.add_job(
                do_job,
                CronTrigger.from_crontab(job.param["cron"]),
                id=str(job.id),
                args=[
                    job.group_id,
                    job.user_id,
                    deserialize_message(job.content),
                    str(job.id),
                ],
            )
        elif job.type == "interval":
            scheduler.add_job(
                do_job,
                **job.param,
                id=str(job.id),
                args=[
                    job.group_id,
                    job.user_id,
                    deserialize_message(job.content),
                    str(job.id),
                ],
            )
        else:
            time = datetime.strptime(job.param["run_date"], "%Y-%m-%d %H:%M:%S")
            scheduler.add_job(
                do_job,
                "date",
                run_date=time,
                id=str(job.id),
                args=[
                    job.group_id,
                    job.user_id,
                    deserialize_message(job.content),
                    str(job.id),
                    True,
                ],
            )
        user_jobs = (
            await session.scalars(select(Schedule).where(Schedule.user_id == user_id))
        ).all()
        await add_task.send(
            f"已添加定时任务, id为[{len(user_jobs)}]，每位用户id独立，使用[查看定时任务 {len(user_jobs)}]查看"
        )


@del_task.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    if not msg:
        await del_task.finish("参数错误，请按照[删除定时任务 任务id]格式发送", at_sender=True)
    if not msg.isdigit():
        await del_task.finish("任务id必须为正整数")
    id_ = int(msg)
    async with create_session() as session:
        user_jobs = (
            await session.scalars(
                select(Schedule).where(Schedule.user_id == event.user_id)
            )
        ).all()
        if id_ <= 0 or id_ > len(user_jobs):
            await del_task.finish(f"用户不存在id为[{msg}]的定时任务，请使用[查看定时任务]查看", at_sender=True)
        try:
            scheduler.remove_job(str(user_jobs[id_ - 1].id))
        except JobLookupError:
            # 似乎过时的date会直接删不掉，抛出这个异常，那就这样
            pass
        await session.delete(user_jobs[id_ - 1])
        await session.commit()
        await del_task.send(f"定时任务id[{msg}]删除成功", at_sender=True)


@show_task.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    async with create_session() as session:
        user_jobs = (
            await session.scalars(
                select(Schedule).where(Schedule.user_id == event.user_id)
            )
        ).all()
        if msg != "":
            if not msg.isdigit():
                await show_task.finish("任务id必须为正整数")
            id_ = int(msg)
            if id_ <= 0 or id_ > len(user_jobs):
                await show_task.finish(
                    f"用户不存在id为[{msg}]的定时任务，请使用[查看定时任务]查看", at_sender=True
                )
            job = user_jobs[id_ - 1]
            if job.type == "cron":
                ret_msg = (
                    f"[id:{id_}]\n类型:cron\n参数:{job.param['cron']}\n内容:"
                    + deserialize_message(job.content)
                )
            elif job.type == "date":
                ret_msg = (
                    f"[id:{id_}]\n类型:date\n参数:{job.param['run_date']}\n内容:"
                    + deserialize_message(job.content)
                )
            elif job.type == "interval":
                pa: str
                for k, v in job.param.items():
                    if k in ["days", "hours", "minutes"]:
                        pa = f"{k}:{v}"
                        break
                ret_msg = (
                    f"[id:{id_}]\n类型:interval\n参数:{pa}\n内容:"
                    + deserialize_message(job.content)
                )
            await show_task.send(ret_msg, at_sender=True)
        else:
            if len(user_jobs) == 0:
                await show_task.send(f"用户不存在定时任务", at_sender=True)
            else:
                ret_msgs = []
                for i, job in enumerate(user_jobs):
                    if (
                        isinstance(event, GroupMessageEvent)
                        and job.group_id != event.group_id
                    ):
                        continue
                    if job.type == "cron":
                        ret_msg = f"[id:{i+1}]\n类型:cron\n参数:{job.param['cron']}\n内容:{job.content}"
                    elif job.type == "date":
                        ret_msg = f"[id:{i+1}]\n类型:date\n参数:{job.param['run_date']}\n内容:{job.content}"
                    elif job.type == "interval":
                        pa: str
                        for k, v in job.param.items():
                            if k in ["days", "hours", "minutes"]:
                                pa = f"{k}:{v}"
                                break
                        ret_msg = f"[id:{i+1}]\n类型:interval\n参数:{pa}\n内容:{job.content}"
                    ret_msgs.append(ret_msg)
                await show_task.finish(
                    (
                        f"用户当前在群[{event.group_id}]的所有定时任务"
                        if isinstance(event, GroupMessageEvent)
                        else f"用户当前所有定时任务"
                    )
                    + MessageSegment.image(
                        pic_to_bytes(
                            text2image(
                                "\n".join(ret_msgs), fontname="Yozai", fontsize=16
                            )
                        )
                    ),
                    at_sender=True,
                )


@show_group_task.handle()
async def _(event: GroupMessageEvent, session: AsyncSession = Depends(get_session)):
    group_jobs = await session.scalars(
        select(Schedule).where(Schedule.group_id == event.group_id)
    )
    ret_msgs = []
    for i, job in enumerate(group_jobs):
        if job.type == "cron":
            ret_msg = f"[id:{i+1}]\n类型:cron\n参数:{job.param['cron']}\n内容:{job.content}"
        elif job.type == "date":
            ret_msg = (
                f"[id:{i+1}]\n类型:date\n参数:{job.param['run_date']}\n内容:{job.content}"
            )
        elif job.type == "interval":
            pa: str
            for k, v in job.param.items():
                if k in ["days", "hours", "minutes"]:
                    pa = f"{k}:{v}"
                    break
            ret_msg = f"[id:{i+1}]\n类型:interval\n参数:{pa}\n内容:{job.content}"
        ret_msgs.append(ret_msg)
    if not ret_msgs:
        await show_group_task.finish("当前群不存在定时任务", at_sender=True)
    await show_task.finish(
        f"当前群[{event.group_id}]的所有定时任务"
        + MessageSegment.image(
            pic_to_bytes(text2image("\n".join(ret_msgs), fontname="Yozai", fontsize=16))
        ),
        at_sender=True,
    )


@del_group_task.handle()
async def _(
    event: GroupMessageEvent,
    arg: Message = CommandArg(),
    session: AsyncSession = Depends(get_session),
):
    group_jobs = (
        await session.scalars(
            select(Schedule).where(Schedule.group_id == event.group_id)
        )
    ).all()
    id_ = arg.extract_plain_text().strip()
    if not id_ or not id_.isdigit():
        await del_group_task("任务id必须为正整数")
    id_ = int(id_)
    if id_ <= 0 or id_ > len(group_jobs):
        await del_group_task.finish(f"当前群不存在id[{id_}]的定时任务，请使用[查看群定时任务]查看")
    belong_to = group_jobs[id_ - 1].user_id
    await session.delete(group_jobs[id_ - 1])
    await session.commit()
    await del_group_task.send(f"已删除群内id为[{id_}]的定时任务，该任务属于用户{belong_to}")


@help_task.handle()
async def _(bot: Bot, event: Union[GroupMessageEvent, PrivateMessageEvent]):
    msgs = []
    msgs.append(
        MessageSegment.node_custom(
            user_id=bot.self_id,
            nickname="定时姬",
            content=f"""
[添加定时任务 任务类型] 来添加
[删除定时任务 任务id] 来删除
[查看定时任务 任务id] 来查看特定定时任务
[查看定时任务] 来查看当前用户所有定时任务

任务类型有
interval:间隔
date:特定日期
cron:cron格式

具体参考提示来进行
""".strip(),
        )
    )
    msgs += [
        MessageSegment.node_custom(
            user_id=bot.self_id, nickname="定时姬", content=MessageSegment.image(url)
        )
        for url in [
            "https://image.cinte.cc/i/2021/05/26/dabd2171ef1bf.png",
            "https://image.cinte.cc/i/2021/05/26/e7f2ea7cbcd16.png",
            "https://image.cinte.cc/i/2021/05/26/edf3057719b1f.png",
        ]
    ]
    if isinstance(event, GroupMessageEvent):
        await bot.send_forward_msg(group_id=event.group_id, messages=msgs)
    else:
        await bot.send_forward_msg(group_id=event.user_id, messages=msgs)
