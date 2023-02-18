"""上古代码，以后一定重写（
"""
from typing import Union
from datetime import datetime

from apscheduler.triggers.cron import CronTrigger
from nonebot import get_bot
from nonebot.adapters.onebot.v11 import (
    Message,
    unescape,
    MessageEvent,
    MessageSegment,
    GroupMessageEvent,
    PrivateMessageEvent,
    Bot,
)
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_imageutils import text2image
from nonebot import on_command, get_driver
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg, ArgStr
from nonebot.typing import T_State
from nonebot.log import logger

from .data_source import (
    cronParse,
    intervalParse,
    dateParse,
    upload_image,
    get_CQ_image,
    get_image_url,
)

from migang.core import ConfigItem, DATA_PATH, get_config
from migang.utils.file import async_load_data, async_save_data
from migang.utils.image import pic_to_bytes

__plugin_meta__ = PluginMetadata(
    name="简易自定义定时消息",
    description="简易自定义定时消息",
    usage="""
usage：
    [添加定时任务 任务类型] 来添加
    [删除定时任务 任务id] 来删除
    [查看定时任务 任务id] 来查看特定定时任务
    [查看定时任务] 来查看当前用户所有定时任务

    任务类型有
    interval:间隔
    date:特定日期
    cron:cron格式

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
__plugin_config__ = ConfigItem(key="smms_token", description="sm.ms的token")

job_list = {}  # qid : {}


schedule_tasks = DATA_PATH / "schedule_reminder" / "schedule_tasks.json"


async def save_jobs():
    global job_list
    await async_save_data(job_list, schedule_tasks)


async def job(gid: int, uid: int, sid: int, msg: str, job_id: str, isOnce=False):
    bot = get_bot()
    try:
        if gid:
            await bot.send_group_msg(
                group_id=gid,
                message=msg,
            )
        elif uid:
            await bot.send_private_msg(
                user_id=uid,
                message=msg,
            )
        else:
            scheduler.remove_job(f"{uid}_{job_id}")
            logger.warning(f"无效定时任务[{uid}_{job_id}]已被自动移除")
    except:
        logger.warning(f"定时任务[{uid}_{job_id}]发送失败")

    if isOnce:
        job_list.get(str(uid)).pop(job_id)
        await save_jobs()


@get_driver().on_startup
async def _():
    global job_list
    job_list = await async_load_data(schedule_tasks)
    for user in job_list:
        jobs = job_list[user]
        for jobR in jobs:
            jobR = jobs[jobR]
            uid = user
            sid = jobR["sid"]
            jobid = jobR["jobId"]
            msg = jobR["msg"]
            gid = jobR["gid"]
            if jobR["type"] == "interval":
                t = jobR["intervalType"]
                interval = jobR["interval"]
                if t == "m":
                    scheduler.add_job(
                        job,
                        "interval",
                        minutes=interval,
                        id=f"{uid}_{jobid}",
                        args=[gid, uid, sid, msg, jobid],
                    )
                elif t == "d":
                    scheduler.add_job(
                        job,
                        "interval",
                        days=interval,
                        id=f"{uid}_{jobid}",
                        args=[gid, uid, sid, msg, jobid],
                    )
                elif t == "h":
                    scheduler.add_job(
                        job,
                        "interval",
                        hours=interval,
                        id=f"{uid}_{jobid}",
                        args=[gid, uid, sid, msg, jobid],
                    )
            elif jobR["type"] == "cron":
                time_setting = jobR["cron"]
                scheduler.add_job(
                    job,
                    CronTrigger.from_crontab(time_setting),
                    id=f"{uid}_{jobid}",
                    args=[gid, uid, sid, msg, jobid],
                )
            elif jobR["type"] == "date":
                try:
                    time = datetime.strptime(jobR["time"], "%Y-%m-%d %H:%M:%S.%f")
                except:
                    time = datetime.strptime(jobR["time"], "%Y-%m-%d %H:%M:%S")
                if time < datetime.now():
                    job_list[user].pop(jobid)
                scheduler.add_job(
                    job,
                    "date",
                    run_date=time,
                    id=f"{uid}_{jobid}",
                    args=[gid, uid, sid, msg, jobid, True],
                )
            logger.info(f"载入定时任务[{uid}_{jobid}]成功")
    await save_jobs()


TYPELIST = {
    # interval
    "interval": 3,
    "间隔": 3,
    # date
    "date": 1,
    "日期": 1,
    "单次": 1,
    "一次": 1,
    "不重复": 1,
    # cron
    "cron": 2,
    "定时": 2,
}

TIMEEXAMPLE = {
    "3": "m:2(表示每2分钟),h:2(表示每2小时),d:2(表示每两天)",
    "1": "2022年1月1日(2022年一月一日触发),2天后(2天后触发),明天1点30分(明天1点30分触发)",
    "2": "https://crontab.guru/",
}


add_task = on_command("添加定时任务", aliases={"/定时任务"}, priority=5, block=True)
del_task = on_command("删除定时任务", priority=5, block=True)
show_task = on_command("查看定时任务", priority=5, block=True)
help_task = on_command("定时任务帮助", priority=5, block=True)


@add_task.handle()
async def _(event: MessageEvent, state: T_State, arg: Message = CommandArg()):
    args = arg.extract_plain_text().strip()
    if args:
        state["job_type"] = args
    user_id = event.user_id
    state["user_id"] = user_id
    if not job_list.get(str(user_id)):
        job_list[str(user_id)] = {}

    jobid = -1
    listjobid = [int(i) for i in job_list[str(user_id)]]
    for i in range(len(listjobid)):
        while listjobid[i] >= 0 and listjobid[i] < len(listjobid) and listjobid[i] != i:
            listjobid[listjobid[i]], listjobid[i] = (
                listjobid[i],
                listjobid[listjobid[i]],
            )
    for i in range(len(listjobid)):
        if listjobid[i] != i:
            jobid = i
            break
    if jobid == -1:
        jobid = len(listjobid)

    state["job_id"] = str(jobid)
    group_id = 0
    if event.message_type == "group":
        if event.sender.role == "member":
            await add_task.finish("群聊中仅允许管理员添加定时任务！")
        group_id = event.group_id
    state["group_id"] = group_id
    state["self_id"] = event.self_id


@add_task.got("job_type", prompt="请发送所选择的定时任务种类")
async def _(state: T_State, job_type: str = ArgStr("job_type")):
    type = -1
    if TYPELIST.get(job_type):
        type = TYPELIST[job_type]
    else:
        await add_task.finish("定时任务类型设置错误，仅支持[date, interval, cron]，具体可发送[定时任务帮助]查看")
    state["type"] = type


@add_task.got("msg_to_sent", prompt="请输入定时任务触发时所要发送的消息")
async def _(state: T_State, msg_to_sent: str = ArgStr("msg_to_sent")):
    msg_to_sent = str(msg_to_sent)
    if msg_to_sent.strip() == "":
        await add_task.finish("定时任务设置错误，消息不得为空")
    msg_to_sent = unescape(msg_to_sent)
    imgs = get_CQ_image(msg_to_sent)
    img_urls = get_image_url(msg_to_sent)
    fail_upload = 0
    if imgs:
        await add_task.send(f"检测到{len(imgs)}张图片，正在上传...")
        for img in imgs:
            if img in img_urls:
                continue
            upload_status = await upload_image(img, await get_config("smms_token"))
            if upload_status and upload_status["success"]:
                msg_to_sent = msg_to_sent.replace(
                    imgs[img], f'[CQ:image,file={upload_status["data"]["url"]}]'
                )
            else:
                fail_upload += 1
    if img_urls:
        for img in img_urls:
            if not imgs.get(img):
                replyMsg = replyMsg.replace(img, f"[CQ:image,file={img}]")
    if fail_upload != 0:
        await add_task.send(f"共{fail_upload}张图片上传失败")
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
    jobid = state["job_id"]
    group_id = state["group_id"]
    self_id = state["self_id"]
    msg_to_sent = state["msg_to_sent"]
    type = state["type"]
    if type == 3:
        check, t, interval = intervalParse(time_setting)
        if not check:
            await add_task.finish(t)
        if t == "m":
            scheduler.add_job(
                job,
                "interval",
                minutes=interval,
                id=f"{user_id}_{jobid}",
                args=[group_id, user_id, self_id, msg_to_sent, jobid],
            )
        elif t == "d":
            scheduler.add_job(
                job,
                "interval",
                days=interval,
                id=f"{user_id}_{jobid}",
                args=[group_id, user_id, self_id, msg_to_sent, jobid],
            )
        elif t == "h":
            scheduler.add_job(
                job,
                "interval",
                hours=interval,
                id=f"{user_id}_{jobid}",
                args=[group_id, user_id, self_id, msg_to_sent, jobid],
            )
        job_list[str(user_id)][jobid] = {
            "type": "interval",
            "interval": interval,
            "intervalType": t,
            "msg": msg_to_sent,
            "gid": group_id,
            "uid": user_id,
            "sid": self_id,
            "jobId": jobid,
        }
    elif type == 1:
        check, time = dateParse(time_setting)
        if not check:
            await add_task.finish(f"参数错误，请参考{TIMEEXAMPLE[str(type)]}，或发送[定时任务帮助]查看")
        if time <= datetime.now():
            await add_task.finish(f"请不要设置过去的时间哦，设定的时间{time}，当前时间{datetime.now()}")
        scheduler.add_job(
            job,
            "date",
            run_date=time,
            id=f"{user_id}_{jobid}",
            args=[group_id, user_id, self_id, msg_to_sent, jobid, True],
        )
        job_list[str(user_id)][jobid] = {
            "type": "date",
            "time": str(time),
            "msg": msg_to_sent,
            "gid": group_id,
            "uid": user_id,
            "sid": self_id,
            "jobId": jobid,
        }
    elif type == 2:
        check, _, _, _ = cronParse(time_setting)
        if not check:
            await add_task.finish(f"参数错误，请参考{TIMEEXAMPLE[str(type)]}，或发送[定时任务帮助]查看")
        scheduler.add_job(
            job,
            CronTrigger.from_crontab(time_setting),
            id=f"{user_id}_{jobid}",
            args=[group_id, user_id, self_id, msg_to_sent, jobid],
        )
        job_list[str(user_id)][jobid] = {
            "type": "cron",
            "cron": time_setting,
            "msg": msg_to_sent,
            "gid": group_id,
            "uid": user_id,
            "sid": self_id,
            "jobId": jobid,
        }
    await save_jobs()

    await add_task.finish(f"已添加定时任务, id为[{jobid}]，每位用户id独立，使用[查看定时任务 {jobid}]查看")


@del_task.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    user_id = event.user_id
    msg = arg.extract_plain_text().strip()
    if not msg:
        await del_task.finish("参数错误，请按照[删除定时任务 任务id]格式发送", at_sender=True)
    if job_list.get(str(user_id)).get(msg):
        try:
            scheduler.remove_job(f"{user_id}_{msg}")
        except:
            logger.info(f"定时任务[{user_id}_{msg}]不存在")
        job_list[str(user_id)].pop(msg)
        await save_jobs()
        await del_task.finish(f"定时任务id[{msg}]删除成功", at_sender=True)
    else:
        await del_task.finish(f"用户不存在id为[{msg}]的定时任务，请使用[查看定时任务]查看", at_sender=True)


@show_task.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    user_id = event.user_id
    msg = arg.extract_plain_text().strip()
    if msg != "":
        if job_list.get(str(user_id)).get(msg):
            details = job_list[str(user_id)][msg]
            type = details["type"]
            if type == "cron":
                ret_msg = f"[id:{details['jobId']}]\n类型:cron\n参数:{details['cron']}\n内容:{details['msg']}"
            elif type == "date":
                ret_msg = f"[id:{details['jobId']}]\n类型:date\n参数:{details['time']}\n内容:{details['msg']}"
            elif type == "interval":
                ret_msg = f"[id:{details['jobId']}]\n类型:interval\n参数:{details['intervalType']}:{details['interval']}\n内容:{details['msg']}"
            await show_task.finish(ret_msg, at_sender=True)
        else:
            await show_task.finish(
                f"用户不存在id为[{msg}]的定时任务，请使用[查看定时任务]查看", at_sender=True
            )
    else:
        if not job_list.get(str(user_id)) or len(job_list.get(str(user_id))) == 0:
            await show_task.finish(f"用户不存在定时任务", at_sender=True)
        else:
            if event.message_type == "group":
                group_id = event.group_id
                ret_msgs = []
                for details in job_list[str(user_id)]:
                    details = job_list[str(user_id)][details]
                    if details["gid"] != group_id:
                        continue
                    type = details["type"]
                    if type == "cron":
                        ret_msgs.append(
                            f"[id:{details['jobId']}]\n类型:cron\n参数:{details['cron']}\n内容:{details['msg']}"
                        )
                    elif type == "date":
                        ret_msgs.append(
                            f"[id:{details['jobId']}]\n类型:date\n参数:{details['time']}\n内容:{details['msg']}"
                        )
                    elif type == "interval":
                        ret_msgs.append(
                            f"[id:{details['jobId']}]\n类型:interval\n参数:{details['intervalType']}:{details['interval']}\n内容:{details['msg']}"
                        )
                await show_task.finish(
                    f"用户当前在群[{group_id}]的所有定时任务"
                    + MessageSegment.image(
                        pic_to_bytes(
                            text2image(
                                "\n".join(ret_msgs), fontname="yz.ttf", fontsize=16
                            )
                        )
                    ),
                    at_sender=True,
                )
            else:
                ret_msgs = []
                for details in job_list[str(user_id)]:
                    details = job_list[str(user_id)][details]
                    type = details["type"]
                    if type == "cron":
                        ret_msgs.append(
                            f"[id:{details['jobId']}]\n类型:cron\n参数:{details['cron']}\n内容:{details['msg']}"
                        )
                    elif type == "date":
                        ret_msgs.append(
                            f"[id:{details['jobId']}]\n类型:date\n参数:{details['time']}\n内容:{details['msg']}"
                        )
                    elif type == "interval":
                        ret_msgs.append(
                            f"[id:{details['jobId']}]\n类型:interval\n参数:{details['intervalType']}:{details['interval']}\n内容:{details['msg']}"
                        )
                await show_task.finish(
                    "用户当前所有定时任务"
                    + MessageSegment.image(
                        pic_to_bytes(
                            text2image(
                                "\n".join(ret_msgs), fontname="yz.ttf", fontsize=16
                            )
                        )
                    ),
                    at_sender=True,
                )


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
