import traceback
from datetime import datetime

from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot import require, on_command
from nonebot.adapters import Bot, Event
from nonebot_plugin_userinfo import UserInfo, EventUserInfo
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import At, Text, Image, Target, UniMessage

from migang.core.cross_platform.message import serialize_message
from migang.core.cross_platform.adapters import supported_adapters
from migang.core.cross_platform import SUPERUSER, Session, UniCmdArg

require("nonebot_plugin_chatrecorder")
from nonebot_plugin_chatrecorder import deserialize_message

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
    type="application",
    supported_adapters=supported_adapters
    | inherit_supported_adapters("nonebot_plugin_userinfo"),
)

__plugin_category__ = "基础功能"
__plugin_aliases__ = ["发消息给维护者"]

feedback = on_command(cmd=".send", aliases={"。send"}, priority=1, block=True)
reply = on_command(
    cmd=".reply", aliases={"。reply"}, priority=1, block=True, permission=SUPERUSER
)


@feedback.handle()
async def _(
    bot: Bot,
    event: Event,
    session: Session,
    arg: UniMessage = UniCmdArg(),
    user_info: UserInfo = EventUserInfo(),
):
    try:
        nickname = user_info.user_name or "#未知昵称#"
        user_id = session.user_id
        timeNow = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        white = int(list(bot.config.superusers)[0])
        if not str(arg).strip():
            await UniMessage("请按照[.send + 您的留言]格式重新发送").send(at_sender=None)
        if session.is_group:
            group_id = session.group_id
            group_name = "#未知群名#"
            if bot.adapter.get_name() == "OneBot V11":
                try:
                    group_info = await bot.get_group_info(group_id=group_id)
                    group_name = group_info["group_name"]
                except Exception as e:
                    logger.info(f"获取群 {group_id} 名称失败：{e}")

            feedback_id = await Feedback.add_feedback(
                user_id=user_id,
                group_id=group_id,
                content=serialize_message(bot=bot, event=event, msg=arg),
            )
            await (
                UniMessage.text(
                    f"留言ID[{feedback_id}]|{timeNow}|@(Q){nickname}({user_id})@(群){group_name}({group_id})\n====================\n"
                )
                + arg.include(Text, Image, At)
            ).send(target=Target(id=white, private=True), bot=bot)
        else:
            feedback_id = await Feedback.add_feedback(
                user_id=user_id,
                group_id=None,
                content=serialize_message(bot=bot, event=event, msg=arg),
            )
            await (
                UniMessage.text(
                    f"留言ID[{feedback_id}]|{timeNow}|@(Q){nickname}({user_id})\n====================\n"
                )
                + arg.include(Text, Image, At)
            ).send(target=Target(id=white, private=True), bot=bot)
        await (
            UniMessage.text(f"您ID为[{feedback_id}]的留言已发送至维护者！\n====================\n")
            + arg.include(Text, Image, At)
        ).send(at_sender=True)
    except Exception as e:
        logger.error(f"记录留言时出错：{traceback.format_exc()}")
        await UniMessage.text("留言发送失败").send(at_sender=True)


@reply.handle()
async def _(bot: Bot, args: UniMessage = UniCmdArg()):
    try:
        feedback_id = str(args[0]).strip().split(" ")[0]
        if feedback_id.isdigit():
            feedback = await Feedback.get_feedback(feedback_id=int(feedback_id))
            if not feedback:
                await UniMessage.text(
                    f"不存在ID[{feedback_id}]的留言,请输入1-{await Feedback.get_max_id()}之间的数字"
                ).send(at_sender=True)
                await reply.finish()
            args[0] = UniMessage.text(str(args[0]).replace(feedback_id, "", 1).lstrip())
            aa = await UniMessage.generate(
                message=deserialize_message(bot_type=bot, msg=feedback.content), bot=bot
            )
            print(type(aa))
            msg = (
                f"关于留言ID[{feedback_id}]的回复\n========原文========\n"
                + await UniMessage.generate(
                    message=deserialize_message(bot_type=bot, msg=feedback.content),
                    bot=bot,
                )
                + "\n========回复========\n"
                + args
            )
            if feedback.group_id:
                await msg.send(Target(id=feedback.group_id), bot=bot)
            else:
                await msg.send(Target(id=feedback.user_id, private=True), bot=bot)
            await UniMessage.text(f"留言ID[{feedback_id}]的回复已发送成功").send(at_sender=True)
        else:
            await UniMessage.text("输入的留言ID有误,请输入数字").send(at_sender=True)
    except Exception as e:
        logger.error(f"回复留言时出错：{e}")
        await reply.send("留言回复失败")
