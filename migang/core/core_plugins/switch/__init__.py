from typing import Tuple

from nonebot.permission import SUPERUSER
from nonebot.params import Command, CommandArg
from nonebot import Driver, get_driver, on_command
from nonebot.adapters.onebot.v11 import (
    GROUP_ADMIN,
    GROUP_OWNER,
    Message,
    GroupMessageEvent,
)

from migang.core.path import DATA_PATH
from migang.core.manager import task_manager, group_manager, plugin_manager

driver: Driver = get_driver()

switch = on_command(
    "开启",
    aliases={"关闭", "开启被动", "关闭被动"},
    priority=1,
    block=True,
    permission=GROUP_ADMIN | GROUP_OWNER,
)


global_switch = on_command(
    "全局开启",
    aliases={"全局关闭", "全局开启被动", "全局关闭被动"},
    priority=1,
    block=True,
    permission=SUPERUSER,
)

USER_HELP_PATH = DATA_PATH / "core" / "help" / "user_help_image"
GROUP_HELP_PATH = DATA_PATH / "core" / "help" / "group_help_image"
GROUP_TASK_PATH = DATA_PATH / "core" / "help" / "group_task_image"


def clean_all_help_image():
    for img in GROUP_HELP_PATH.iterdir():
        img.unlink()
    for img in USER_HELP_PATH.iterdir():
        img.unlink()


def clean_group_help_image():
    for img in GROUP_TASK_PATH.iterdir():
        img.unlink()


def clean_group_help_image(group_id: int):
    if (file := GROUP_HELP_PATH / f"{group_id}.png").exists():
        file.unlink()


def clean_group_task_image(group_id: int):
    if (file := GROUP_TASK_PATH / f"{group_id}.png").exists():
        file.unlink()


@switch.handle()
async def _(
    event: GroupMessageEvent,
    cmd: Tuple[str, ...] = Command(),
    arg: Message = CommandArg(),
):
    cmd = cmd[0]
    param = arg.extract_plain_text().strip()
    if not param:
        await switch.finish()
    if param == "全部插件":
        count = 0
        if cmd == "开启":
            for plugin in plugin_manager.get_plugin_name_list():
                if not await group_manager.set_plugin_enable(
                    plugin_name=plugin, group_id=event.group_id
                ):
                    count += 1
        else:
            for plugin in plugin_manager.get_plugin_name_list():
                if not await group_manager.set_plugin_disable(
                    plugin_name=plugin, group_id=event.group_id
                ):
                    count += 1
        clean_group_help_image(event.group_id)
        await switch.finish(
            f"已{cmd}全部插件"
            + (f"，不包括{count}个全局禁用与无权限插件" if "cmd" == "开启" and count != 0 else "")
        )
    elif param == "全部被动":
        count = 0
        if cmd == "开启":
            for task in task_manager.get_task_name_list():
                if not await group_manager.set_task_enable(
                    task_name=task, group_id=event.group_id
                ):
                    count += 1
        else:
            for task in task_manager.get_task_name_list():
                if not await group_manager.set_task_disable(
                    task_name=task, group_id=event.group_id
                ):
                    count += 1
        clean_group_task_image(event.group_id)
        await switch.finish(
            f"已{cmd}全部被动"
            + (f"，不包括{count}个全局禁用与无权限被动" if "cmd" == "开启" and count != 0 else "")
        )
    if cmd in ("开启被动", "关闭被动") and (name := task_manager.get_task_name(param)):
        if cmd == "开启被动" and not await group_manager.set_task_enable(
            task_name=name, group_id=event.group_id
        ):
            await switch.finish(f"插件 {param} 已被全局禁用或权限不足，无法开启")
        elif cmd == "关闭被动":
            await group_manager.set_task_disable(
                task_name=name, group_id=event.group_id
            )
        clean_group_task_image(event.group_id)
        await switch.finish(f"已{cmd}群被动：{param}")
    if name := plugin_manager.get_plugin_name(param):
        if cmd == "开启" and not await group_manager.set_plugin_enable(
            plugin_name=name, group_id=event.group_id
        ):
            await switch.finish(f"插件 {param} 已被全局禁用或权限不足，无法开启")
        elif cmd == "关闭" and not await group_manager.set_plugin_disable(
            plugin_name=name, group_id=event.group_id
        ):
            await switch.finish(f"插件 {param} 不可被禁用")
        clean_group_help_image(event.group_id)
        await switch.finish(f"已{cmd}插件：{param}")
    elif name := task_manager.get_task_name(param):
        if cmd == "开启" and not await group_manager.set_task_enable(
            task_name=name, group_id=event.group_id
        ):
            await switch.finish(f"插件 {param} 已被全局禁用或权限不足，无法开启")
        elif cmd == "关闭":
            await group_manager.set_task_disable(
                task_name=name, group_id=event.group_id
            )
        clean_group_task_image(event.group_id)
        await switch.finish(f"已{cmd}群被动：{param}")
    else:
        await switch.finish(f"插件或群被动 {param} 不存在")


@global_switch.handle()
async def _(
    cmd: Tuple[str, ...] = Command(),
    arg: Message = CommandArg(),
):
    cmd = cmd[0]
    param = arg.extract_plain_text().strip()
    if not param:
        await switch.finish()
    if param == "全部插件":
        if cmd == "全局开启":
            for plugin in plugin_manager.get_plugin_name_list():
                await plugin_manager.enable_plugin(plugin_name=plugin)
        else:
            for plugin in plugin_manager.get_plugin_name_list():
                await plugin_manager.disable_plugin(plugin_name=plugin)
        clean_all_help_image()
        await switch.finish(f"已{cmd}全部插件")
    elif param == "全部被动":
        if cmd == "全局开启":
            for task in task_manager.get_task_name_list():
                await task_manager.enable_task(task_name=task)
        else:
            for task in task_manager.get_task_name_list():
                await task_manager.disable_task(task_name=task)
        await clean_all_task_image()
        await switch.finish(f"已{cmd}全部被动")

    if cmd in ("全局开启被动", "全局关闭被动") and (name := task_manager.get_task_name(param)):
        if cmd == "全局开启被动":
            await task_manager.enable_task(task_name=name)
        elif cmd == "全局关闭被动":
            await task_manager.disable_task(task_name=name)
        await clean_all_task_image()
        await switch.finish(f"已{cmd}群被动：{param}")
    if name := plugin_manager.get_plugin_name(param):
        if cmd == "全局开启":
            await plugin_manager.enable_plugin(plugin_name=name)
        elif cmd == "全局关闭":
            await plugin_manager.disable_plugin(plugin_name=name)
        clean_all_help_image()
        await switch.finish(f"已{cmd}插件：{param}")
    elif name := task_manager.get_task_name(param):
        if cmd == "全局开启":
            await task_manager.enable_task(task_name=name)
        elif cmd == "全局关闭":
            await task_manager.disable_task(task_name=name)
        await clean_all_task_image()
        await switch.finish(f"已{cmd}群被动：{param}")
    else:
        await switch.finish(f"插件或群被动 {param} 不存在")
