"""获取帮助图片、插件帮助、群被动状态
"""

import re
from io import BytesIO
from pathlib import Path
from typing import Set, List, Union

import anyio
from pil_utils import text2image
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot import require, get_plugin, on_command
from nonebot.permission import SUPERUSER, SuperUser
from nonebot.rule import (
    ToMeRule,
    RegexRule,
    CommandRule,
    EndswithRule,
    KeywordsRule,
    FullmatchRule,
    StartswithRule,
    to_me,
)
from nonebot.adapters.onebot.v11 import (
    GROUP,
    Bot,
    Message,
    MessageEvent,
    MessageSegment,
    GroupMessageEvent,
    PrivateMessageEvent,
)

from migang.core.manager import user_manager, group_manager, plugin_manager

from .data_source import (
    USER_HELP_PATH,
    GROUP_HELP_PATH,
    GROUP_TASK_PATH,
    draw_usage,
    get_help_image,
    get_task_image,
    get_plugin_help,
)

require("nonebot_plugin_htmlrender")

__plugin_meta__ = PluginMetadata(
    name="帮助",
    description="显示各种帮助信息",
    usage="""
usage：
    所有指令都需要at
    指令：
        显示功能列表：帮助
        显示插件帮助：帮助[xxx]
        显示插件指令：指令帮助[xxx]
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

simple_help = on_command("帮助", aliases={"功能"}, priority=1, block=True, rule=to_me())
task_help = on_command("群被动状态", priority=1, block=True, permission=GROUP)
command_list = on_command(
    "指令列表", aliases={"指令帮助"}, priority=1, block=True, rule=to_me()
)


@simple_help.handle()
async def _(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    """
    获取机器人帮助图片或指定插件的帮助信息。
    参数:
      args: 插件名，留空则返回总帮助图片。
    """
    args = args.extract_plain_text()
    if not args:
        image_file: Path
        group_id, user_id = None, None
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
            image_file = GROUP_HELP_PATH / f"{group_id}.png"
        elif isinstance(event, PrivateMessageEvent):
            user_id = event.user_id
            image_file = USER_HELP_PATH / f"{user_id }.png"
        if image_file.exists():
            await simple_help.finish(MessageSegment.image(image_file))
        img = await get_help_image(
            group_id=group_id,
            user_id=user_id,
            super_user=await SUPERUSER(bot, event),
        )
        await simple_help.send(MessageSegment.image(img))
        async with await anyio.open_file(image_file, "wb") as f:
            await f.write(img)
    else:
        if help_ := get_plugin_help(args):
            await simple_help.send(await draw_usage(help_))
        else:
            await simple_help.send("没有该插件的帮助信息")


@task_help.handle()
async def _(event: GroupMessageEvent):
    image_file = GROUP_TASK_PATH / f"{event.group_id}.png"
    if image_file.exists():
        await task_help.finish(MessageSegment.image(image_file))
    img = await get_task_image(event.group_id)
    await task_help.send(MessageSegment.image(img))
    async with await anyio.open_file(image_file, "wb") as f:
        await f.write(img)


@command_list.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    name = args.extract_plain_text()
    if (plugin_name := plugin_manager.get_plugin_name(name)) is None:
        await command_list.finish(f"插件 {name} 不存在！")
    else:
        if (
            (
                isinstance(event, GroupMessageEvent)
                and not group_manager.check_plugin_permission(
                    plugin_name=plugin_name, group_id=event.group_id
                )
            )
            or isinstance(event, PrivateMessageEvent)
            and not user_manager.check_plugin_permission(
                plugin_name=plugin_name, user_id=event.user_id
            )
        ):
            await command_list.finish(f"当前用户/群权限不足，无法查看插件 {name} 的信息")
        plugin = get_plugin(plugin_name)
        matchers = plugin.matcher
        commands = {
            "私聊可用指令": {},
            "群员可用指令": {},
            "群管理员可用指令": {},
            "群主可用指令": {},
            "超级用户指令": {},
        }
        for matcher in matchers:
            matcher_permissions: Set[str] = set()
            for perm in matcher.permission.checkers:
                if isinstance(perm.call, SuperUser):
                    matcher_permissions.add("超级用户指令")
                else:
                    if perm.call.__name__ == "_group":
                        matcher_permissions |= set(["群员可用指令", "群管理员可用指令", "群主可用指令"])
                    elif perm.call.__name__ == "_group_member":
                        matcher_permissions.add("群员可用指令")
                    elif perm.call.__name__ == "_group_admin":
                        matcher_permissions.add("群管理员可用指令")
                    elif perm.call.__name__ == "_group_owner":
                        matcher_permissions.add("群主可用指令")
                    elif perm.call.__name__ == "_private_friend":
                        matcher_permissions.add("私聊可用指令")
            if not matcher_permissions:
                matcher_permissions = set(["群员可用指令", "群管理员可用指令", "群主可用指令", "私聊可用指令"])
            to_me = False
            for dep in matcher.rule.checkers:
                if isinstance(dep.call, ToMeRule):
                    to_me = True
                    break

            def add_to_commands(type_: str, cmds: Union[str, List[str]]):
                for perm in matcher_permissions:
                    if type_ not in commands[perm]:
                        commands[perm][type_] = set()
                if isinstance(cmds, str):
                    cmds = [cmds]
                if isinstance(cmds, re.Pattern):
                    cmds = [cmds.pattern]
                cmd_set = set()
                for cmd in cmds:
                    if isinstance(cmd, str):
                        cmd = [cmd]
                    for c in cmd:
                        cmd_set.add(c)

                cmd_text = " | ".join(
                    [f"[b]{cmd}[/b]" if to_me else cmd for cmd in cmd_set]
                )
                for perm in matcher_permissions:
                    commands[perm][type_].add(cmd_text)

            for dep in matcher.rule.checkers:
                if isinstance(dep.call, FullmatchRule):
                    add_to_commands(type_="完全匹配", cmds=dep.call.msg)
                elif isinstance(dep.call, CommandRule):
                    add_to_commands(type_="指令", cmds=dep.call.cmds)
                elif isinstance(dep.call, StartswithRule):
                    add_to_commands(type_="前缀匹配", cmds=dep.call.msg)
                elif isinstance(dep.call, EndswithRule):
                    add_to_commands(type_="后缀匹配", cmds=dep.call.msg)
                elif isinstance(dep.call, RegexRule):
                    add_to_commands(type_="正则匹配", cmds=dep.call.regex)
                elif isinstance(dep.call, KeywordsRule):
                    add_to_commands(type_="关键词匹配", cmds=dep.call.keywords)

        cmd_text = [f"插件 {name} 可用指令如下，加粗指令表示需要@Bot"]
        for perm_text, cmds in commands.items():
            if not cmds:
                continue
            text = f"[align=center][size=30][color=#a3c9eb]{perm_text}[/color][/size][/align]"
            for k, v in cmds.items():
                text += f"\n[size=25][color=#FA876F]{k}[/color][/size]\n" + "\n".join(
                    [f"[size=20]{s}[/size]" for s in v]
                )
            cmd_text.append(text)
        if len(cmd_text) == 1:
            cmd_img = text2image(text="该插件无可用指令")
        else:
            cmd_img = text2image(text="\n".join(cmd_text))
        with BytesIO() as buf:
            cmd_img.save(buf, format="PNG")
            await command_list.send(MessageSegment.image(buf))
