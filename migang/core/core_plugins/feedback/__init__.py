from datetime import datetime

from nonebot import on_command
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, GroupMessageEvent

from migang.core.models import Feedback

__plugin_meta__ = PluginMetadata(
    name="嘀嘀嘀",
    description="发消息给维护者",
    usage="""
usage：
    发送消息给维护者
    指令：
        .send xxx
""".strip(),
    extra={
        "unique_name": "migang_feedback",
        "example": ".send 早上好",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_category__ = "基础功能"
__plugin_aliases__ = ["发消息给维护者"]

feedback = on_command(cmd=".send", aliases={"。send"}, priority=1, block=True)
reply = on_command(
    cmd=".reply", aliases={"。reply"}, priority=1, block=True, permission=SUPERUSER
)


@feedback.handle()
async def _(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    try:
        nickname = event.sender.nickname or "#未知昵称#"
        user_id = event.user_id
        text = str(arg).strip()
        timeNow = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        white = int(list(bot.config.superusers)[0])
        if not text:
            await feedback.finish("请按照[.send + 您的留言]格式重新发送", at_sender=True)
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
            group_name = "#未知群名#"
            try:
                group_info = await bot.get_group_info(group_id=group_id)
                group_name = group_info["group_name"]
            except Exception as e:
                logger.info(f"获取群 {group_id} 名称失败")

            feedback_id = await Feedback.add_feedback(
                user_id=user_id, group_id=group_id, content=text
            )
            await bot.send_private_msg(
                user_id=white,
                message=f"留言ID[{feedback_id}]|{timeNow}|@(Q){nickname}({user_id})@(群){group_name}({group_id})\n====================\n{text}",
            )
        else:
            feedback_id = await Feedback.add_feedback(
                user_id=user_id, group_id=None, content=text
            )
            await bot.send_private_msg(
                user_id=white,
                message=f"留言ID[{feedback_id}]|{timeNow}|@(Q){nickname}({user_id})\n====================\n{text}",
            )
        await feedback.send(
            message=Message(
                f"您ID为[{feedback_id}]的留言已发送至维护者！\n====================\n{text}"
            ),
            at_sender=True,
        )
    except Exception as e:
        logger.error(f"记录留言时出错：{e}")
        await feedback.send("留言发送失败", at_sender=True)


@reply.handle()
async def _(bot: Bot, arg: Message = CommandArg()):
    try:
        msg = str(arg).strip()
        feedback_id = msg.split(" ")[0]
        if feedback_id.isdigit():
            feedback = await Feedback.get_feedback(feedback_id=int(feedback_id))
            if not feedback:
                await reply.send(
                    f"不存在ID[{feedback_id}]的留言,请输入1-{await Feedback.get_max_id()}之间的数字",
                    at_sender=True,
                )
                return
            reply_text = Message(msg.lstrip(feedback_id).strip())
            msg = f"关于留言ID[{feedback_id}]的回复\n========原文========\n{Message(feedback.content)}\n========回复========\n{reply_text}"
            if feedback.group_id:
                await bot.send_group_msg(group_id=feedback.group_id, message=msg)
            else:
                await bot.send_private_msg(user_id=feedback.user_id, message=msg)
            await reply.send(f"留言ID[{feedback_id}]的回复已发送成功", at_sender=True)
        else:
            await reply.send(f"输入的留言ID有误,请输入数字", at_sender=True)
    except Exception as e:
        logger.error(f"回复留言时出错：{e}")
        await reply.send("留言回复失败")
