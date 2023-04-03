from typing import Tuple

from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata
from nonebot.params import Arg, CommandArg, RegexGroup
from nonebot import on_regex, on_notice, on_command, on_fullmatch
from nonebot.adapters.onebot.v11 import (
    GROUP,
    Bot,
    Message,
    MessageSegment,
    GroupMessageEvent,
    GroupIncreaseNoticeEvent,
)

from migang.core.models import GroupWelcome

from .data_source import serialize_message, deserialize_message

__plugin_meta__ = PluginMetadata(
    name="群欢迎语",
    description="设置群欢迎语",
    usage="""
指令：
    设置群欢迎语
    删除群欢迎语
    查看群欢迎语
    禁用群欢迎语
    启用群欢迎语
说明：
    前两个指令会修改欢迎语
    后两个指令仅改变欢迎语的启用状态
""".strip(),
    extra={
        "unique_name": "migang_group_welcome",
        "example": "rua",
        "author": "migang",
        "version": 0.1,
    },
)

__plugin_category__ = "群功能"

change_group_welcome = on_command(
    "设置群欢迎语",
    priority=1,
    permission=GROUP,
    block=True,
)

change_status = on_regex(
    r"^(删除|禁用|启用)群欢迎语$",
    priority=1,
    permission=GROUP,
    block=True,
)

show_group_welcome = on_fullmatch("查看群欢迎语", priority=1, permission=GROUP, block=True)


def _rule_group_increase(event: GroupIncreaseNoticeEvent) -> bool:
    return event.user_id != event.self_id


group_increase = on_notice(priority=1, block=False, rule=_rule_group_increase)


@change_group_welcome.handle()
async def _(
    matcher: Matcher,
    args: Message = CommandArg(),
):
    if args:
        matcher.set_arg("content", args)


@change_group_welcome.got("content", prompt="请输入需要设置的群欢迎语~")
async def _(event: GroupMessageEvent, content: Message = Arg("content")):
    group_welcome, _ = await GroupWelcome.get_or_create(group_id=event.group_id)
    group_welcome.content = await serialize_message(content)
    await group_welcome.save(update_fields=["content"])
    await change_group_welcome.send(
        "已成功设置群欢迎语：\n" + deserialize_message(group_welcome.content)
    )


@change_status.handle()
async def _(event: GroupMessageEvent, regex_group: Tuple[str, ...] = RegexGroup()):
    cmd = regex_group[0]
    group_welcome = await GroupWelcome.filter(group_id=event.group_id).first()
    if not group_welcome:
        await change_status.finish("当前群未设置群欢迎语哦~")
    if cmd == "删除":
        group_welcome.content = None
        await group_welcome.save(update_fields=["content"])
    else:
        group_welcome.status = cmd == "启用"
        await group_welcome.save(update_fields=["status"])
    await change_status.send(f"已{cmd}当前群的欢迎语~")


@show_group_welcome.handle()
async def _(event: GroupMessageEvent):
    group_welcome = await GroupWelcome.filter(group_id=event.group_id).first()
    if not group_welcome or group_welcome.content is None:
        await show_group_welcome.finish("当前群未设置群欢迎语哦~")
    await show_group_welcome.send(deserialize_message(group_welcome.content))


@group_increase.handle()
async def _(event: GroupIncreaseNoticeEvent):
    group_welcome = await GroupWelcome.filter(group_id=event.group_id).first()
    if not group_welcome or not group_welcome.status or group_welcome.content is None:
        return
    await group_increase.send(
        MessageSegment.at(event.user_id) + deserialize_message(group_welcome.content)
    )
