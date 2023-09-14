"""处理和群还有好友相关的一些邀请，退群事件
"""
import asyncio
from io import BytesIO
from datetime import datetime
from typing import Tuple, Union

from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from pil_utils import BuildImage, text2image
from nonebot.params import Command, Fullmatch, CommandArg, RegexGroup
from nonebot import require, on_regex, on_notice, on_command, on_request, on_fullmatch
from nonebot.adapters.onebot.v11 import (
    Bot,
    Message,
    ActionFailed,
    MessageSegment,
    GroupMessageEvent,
    GroupRequestEvent,
    FriendRequestEvent,
    PrivateMessageEvent,
    FriendAddNoticeEvent,
    GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent,
)

from migang.core.manager import request_manager, permission_manager
from migang.core import BLACK, ConfigItem, get_config, sync_get_config

from .data_source import build_request_img

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic

__plugin_meta__ = PluginMetadata(
    name="好友与群邀请退群等事件处理",
    description="处理好友与群聊中的邀请等事件",
    usage="""
usage：
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

__plugin_always_on__ = True
__plugin_hidden__ = True
__plugin_category__ = "基础功能"

__plugin_config__ = (
    ConfigItem(
        key="handle_friend",
        initial_value="询问",
        default_value="询问",
        description="如何处理好友请求：询问，同意，拒绝",
    ),
    ConfigItem(
        key="handle_group",
        initial_value="询问",
        default_value="询问",
        description="如何处理入群请求：询问，同意，拒绝",
    ),
    ConfigItem(
        key="group_request_hint",
        initial_value="想要拉我入群吗，正在询问管理员哦~请耐心等待",
        default_value="",
        description="当入群请求为询问状态时，发送给请求者的话",
    ),
    ConfigItem(
        key="reject_group_reason",
        initial_value="",
        default_value="",
        description="拒绝入群请求时候的原因",
    ),
    ConfigItem(
        key="auto_leave",
        initial_value=True,
        default_value=True,
        description="当handle_group为拒绝或询问时，是否自动退出被强拉的群",
    ),
    ConfigItem(
        key="auto_leave_info",
        initial_value="咦，这是哪？走了哦",
        default_value="",
        description="当handle_group为拒绝或询问时，是否自动退出被强拉的群",
    ),
    ConfigItem(
        key="firend_help",
        initial_value="欢迎和米缸成为好朋友哦~",
        default_value="",
        description="成功加好友时发送的帮助语句，该语句可用/帮助呼出",
    ),
    ConfigItem(
        key="group_help",
        initial_value="咦~是没见过的群呢",
        default_value="",
        description="成功入群时发送的帮助语句，该语句可用/帮助呼出",
    ),
    ConfigItem(
        key="custom_help",
        initial_value={
            "关于": {
                "text": "https://github.com/LambdaYH/MigangBot",
                "text_to_image": False,
            }
        },
        default_value=[],
        description="自定义帮助，参照案例，发送[.help keyword]即可显示出，text_to_image即是否用图片形式发送（md格式），否则则转换为Message",
    ),
)

help_msg = on_command(".help", aliases={"。help", "/帮助"}, block=True, priority=1)
friend_request = on_request(priority=1, block=True)
group_request = on_request(priority=1, block=True)
show_request = on_fullmatch(
    ("查看所有请求", "查看好友请求", "查看入群请求"), permission=SUPERUSER, block=True, priority=1
)
reset_request = on_fullmatch(
    ("清空所有请求", "清空好友请求", "清空入群请求"), priority=1, permission=SUPERUSER
)
allow_group = on_command("认证群", priority=1, permission=SUPERUSER)
handle_request = on_command(
    "同意入群请求",
    aliases={"同意好友请求", "拒绝入群请求", "拒绝好友请求"},
    priority=1,
    block=True,
    permission=SUPERUSER,
)
change_request_handle = on_regex(
    r"^修改(群|好友)请求处理方式(询问|同意|拒绝)$", priority=1, block=False, permission=SUPERUSER
)


def _rule_group_increase(event: GroupIncreaseNoticeEvent) -> bool:
    return event.user_id == event.self_id


def _rule_group_decrease(event: GroupDecreaseNoticeEvent) -> bool:
    return event.sub_type == "kick_me"


def _rule_friend_add(event: FriendAddNoticeEvent) -> bool:
    return True


group_increase = on_notice(priority=1, block=False, rule=_rule_group_increase)
group_decrease = on_notice(priority=1, block=False, rule=_rule_group_decrease)
friend_add = on_notice(priority=1, block=False, rule=_rule_friend_add)

# 不强制退出的群
allowed_group = set()

_handle_group = sync_get_config(key="handle_group", default_value="询问")
_handle_friend = sync_get_config(key="handle_friend", default_value="询问")


@friend_request.handle()
async def _(bot: Bot, event: FriendRequestEvent):
    user_name, sex, age = None, None, None
    try:
        user = await bot.get_stranger_info(user_id=event.user_id)
        user_name = user["nickname"]
        sex = user["sex"]
        age = user["age"]
    except ActionFailed:
        logger.info(f"无法获取用户 {event.user_id} 的信息")
    for user in bot.config.superusers:
        await bot.send_private_msg(
            user_id=int(user),
            message=f"*****一份好友申请*****\n"
            f"昵称：{user_name}({event.user_id})\n"
            f"状态：{_handle_friend}\n"
            f"日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"备注：{event.comment}",
        )
    if _handle_friend == "同意":
        try:
            await bot.set_friend_add_request(flag=event.flag, approve=True)
            logger.info(f"已同意好友请求：{event.user_id}")
        except ActionFailed:
            logger.info(f"同意好友请求失败：{event.user_id}")
    elif _handle_friend == "拒绝":
        try:
            await bot.set_friend_add_request(flag=event.flag, approve=False)
            logger.info(f"已拒绝好友请求：{event.user_id}")
        except ActionFailed:
            logger.info(f"拒绝好友请求失败：{event.user_id}")
    else:
        await request_manager.add(
            user_name=user_name,
            user_id=event.user_id,
            sex=sex,
            age=age,
            comment=event.comment,
            flag=event.flag,
            time=datetime.now(),
        )


@group_request.handle()
async def _(bot: Bot, event: GroupRequestEvent):
    if event.sub_type != "invite":
        return
    if str(event.user_id) in bot.config.superusers:
        try:
            allowed_group.add(event.group_id)
            await bot.set_group_add_request(
                flag=event.flag, sub_type="invite", approve=True
            )
            for user in bot.config.superusers:
                await bot.send_private_msg(
                    user_id=int(user),
                    message="我直接光速同意.jpg(๑¯◡¯๑)",
                )
            await group_request.finish()
        except ActionFailed:
            for user in bot.config.superusers:
                await bot.send_private_msg(
                    user_id=int(user),
                    message="还没反应过来我就在里面了呢~",
                )
            await group_request.finish()
    user_name, sex, age = None, None, None
    try:
        user = await bot.get_stranger_info(user_id=event.user_id)
        user_name = user["nickname"]
        sex = user["sex"]
        age = user["age"]
    except ActionFailed:
        logger.info(f"无法获取用户 {event.user_id} 的信息")
    group_name = None
    try:
        group = await bot.get_group_info(group_id=event.group_id)
        group_name = group["group_name"]
    except ActionFailed:
        logger.info(f"无法获取群 {event.group_id} 的信息")
    for user in bot.config.superusers:
        await bot.send_private_msg(
            user_id=int(user),
            message=f"*****一份入群申请*****\n"
            f"群聊：{group_name}({event.group_id})\n"
            f"申请人：{user_name}({event.user_id})\n"
            f"状态：{_handle_group}\n"
            f"日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        )
    if _handle_group == "同意":
        try:
            await bot.set_group_add_request(
                flag=event.flag, sub_type="invite", approve=True
            )
            logger.info(f"已入群请求：{event.group_id}")
        except ActionFailed:
            logger.info(f"入群请求失败：{event.group_id}")
    elif _handle_group == "拒绝":
        try:
            reason = await get_config("reject_group_reason")
            if reason is None:
                reason = ""
            await bot.set_group_add_request(
                flag=event.flag, sub_type="invite", approve=False, reason=reason
            )
            logger.info(f"已拒绝入群请求：{event.group_id}")
        except ActionFailed:
            logger.info(f"拒绝入群请求失败：{event.group_id}")
    else:
        if hint := await get_config("group_request_hint"):
            await bot.send_private_msg(user_id=event.user_id, message=Message(hint))
        await request_manager.add(
            user_name=user_name,
            user_id=event.user_id,
            sex=sex,
            age=age,
            comment=event.comment,
            flag=event.flag,
            time=datetime.now(),
            group_id=event.group_id,
            group_name=group_name,
        )


@show_request.handle()
async def _(cmd: str = Fullmatch()):
    cmd = cmd[2:4]
    data = request_manager.get_requests()
    if cmd == "入群":
        await show_request.send(
            MessageSegment.image(
                (await build_request_img(data.group_request, "group")).save_png()
            )
        )
    elif cmd == "好友":
        await show_request.send(
            MessageSegment.image(
                (await build_request_img(data.friend_request, "friend")).save_png()
            )
        )
    else:
        friend_req_img = await build_request_img(data.friend_request, "friend")
        group_req_img = await build_request_img(data.group_request, "group")
        img = BuildImage.new(
            mode="RGBA",
            size=(
                max(friend_req_img.width, group_req_img.width),
                friend_req_img.height + group_req_img.height,
            ),
        )
        img.paste(friend_req_img, alpha=True)
        img.paste(group_req_img, pos=(0, friend_req_img.height), alpha=True)
        await show_request.send(MessageSegment.image(img.save_png()))


@handle_request.handle()
async def _(bot: Bot, cmds: Tuple[str, ...] = Command(), args: Message = CommandArg()):
    id_: str = args.extract_plain_text()
    if not id_.isdigit():
        await handle_request.finish("请输入有效的数字")
    id_ = int(id_)
    cmd = "group" if cmds[0][2:4] == "入群" else "friend"
    approve = cmds[0][:2] == "同意"
    if approve:
        if cmd == "group" and (group := request_manager.get_group_request(id_=id_)):
            allowed_group.add(group.group_id)
        await handle_request.send(
            await request_manager.approve(bot=bot, id_=id_, type_=cmd)
        )
    else:
        await handle_request.send(
            await request_manager.reject(
                bot=bot, id_=id_, type_=cmd, reason=cmds[0][6:].strip()
            )
        )


@reset_request.handle()
async def _(cmd: str = Fullmatch()):
    cmd = cmd[2:4]
    if cmd == "所有":
        await request_manager.reset(None)
    elif cmd == "入群":
        await request_manager.reset("group")
    else:
        await request_manager.reset("friend")
    await reset_request.send(f"已清空{cmd}请求")


@help_msg.handle()
async def _(
    bot: Bot,
    event: Union[GroupMessageEvent, PrivateMessageEvent],
    arg: Message = CommandArg(),
):
    msg = arg.extract_plain_text()
    if not msg:
        if isinstance(event, GroupMessageEvent):
            await help_msg.finish(Message(await get_config("group_help")))
        elif isinstance(event, PrivateMessageEvent):
            await help_msg.finish(Message(await get_config("firend_help")))
    if msg == "设定":
        with BytesIO() as buf:
            text2image(
                text=f"""
[b]姓名[/b]: {list(bot.config.nickname)[0]}
[b]master[/b]: {list(bot.config.superusers)[0]}
[b]好友请求处理[/b]: {await get_config('handle_friend')}
[b]入群请求处理[/b]: {await get_config('handle_group')}
        """.strip(),
                fontname="Yozai",
                fontsize=15,
            ).save(buf, "PNG")
            await help_msg.finish(MessageSegment.image(buf))

    if help_ := (await get_config("custom_help")).get(msg):
        if help_["text_to_image"]:
            await help_msg.send(
                message=MessageSegment.image(await md_to_pic(help_["text"]))
            )
        else:
            await help_msg.send(message=Message(help_["text"]))
    else:
        await help_msg.send(f"没有关于 {msg} 的帮助信息")


@change_request_handle.handle()
async def _(reg_group: Tuple[str, ...] = RegexGroup()):
    if reg_group[1] not in ("同意", "询问", "拒绝"):
        await change_request_handle.finish("方式必须为 同意/询问/拒绝！")
    if reg_group[0] == "群":
        global _handle_group
        _handle_group = reg_group[1]
    else:
        global _handle_friend
        _handle_friend = reg_group[1]
    await change_request_handle.send(f"处理{reg_group[0]}方式已更改为{reg_group[1]}，下次重启前有效")


@allow_group.handle()
async def _(arg: Message = CommandArg()):
    group_id = arg.extract_plain_text()
    if not group_id.isdigit():
        await allow_group.finish(f"群号 {group_id} 不是一个合法数字！")
    allowed_group.add(int(group_id))
    await allow_group.send(f"已认证群 {group_id}，在下次重启前有效")


@group_increase.handle()
async def _(bot: Bot, event: GroupIncreaseNoticeEvent):
    if (
        _handle_group != "同意"
        and (await get_config("auto_leave"))
        and (event.group_id not in allowed_group)
    ):
        await bot.send_group_msg(
            group_id=event.group_id,
            message=Message(await get_config("auto_leave_info")),
        )
        await bot.set_group_leave(group_id=event.group_id)
        await asyncio.sleep(0.5)
        await bot.send_private_msg(
            user_id=int(list(bot.config.superusers)[0]),
            message=f"已自动退出群聊 {event.group_id}",
        )
    else:
        await asyncio.sleep(2)
        await bot.send_group_msg(
            group_id=event.group_id, message=Message(await get_config("group_help"))
        )


@group_decrease.handle()
async def _(bot: Bot, event: GroupDecreaseNoticeEvent):
    operator_id = event.operator_id
    group_id = event.group_id
    try:
        info = await bot.get_stranger_info(user_id=operator_id)
        operator_name = info["nickname"]
    except ActionFailed:
        operator_name = "None"
    try:
        info = await bot.get_group_info(group_id=group_id)
        group_name = info["group_name"]
    except ActionFailed:
        group_name = "None"
    await bot.send_private_msg(
        user_id=int(list(bot.config.superusers)[0]),
        message=f"****呜..一份踢出报告****\n"
        f"我被 {operator_name}({operator_id})\n"
        f"踢出了 {group_name}({group_id})\n"
        f"日期：{str(datetime.now()).split('.')[0]}",
    )
    if event.group_id in allowed_group:
        allowed_group.remove(event.group_id)
    permission_manager.set_group_perm(event.group_id, permission=BLACK)
    permission_manager.set_user_perm(event.user_id, permission=BLACK)
    logger.info(f"已拉黑用户 {operator_name}({operator_id}) 与群 {group_name}({group_id})")


@friend_add.handle()
async def _():
    await asyncio.sleep(2)
    await friend_add.send(message=Message(await get_config("firend_help")))
