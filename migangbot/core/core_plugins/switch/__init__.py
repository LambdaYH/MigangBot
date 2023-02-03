from typing import Tuple

from nonebot.params import Command, CommandArg
from nonebot.permission import SUPERUSER
from nonebot import Driver, get_driver, on_command
from nonebot.adapters.onebot.v11 import (
    GROUP_ADMIN,
    GROUP_OWNER,
    Message,
    GroupMessageEvent,
)

from migangbot.core.path import DATA_PATH
from migangbot.core.manager import plugin_manager, group_manager, task_manager

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


def CleanAllHelpImage():
    for img in GROUP_HELP_PATH.iterdir():
        img.unlink()
    for img in USER_HELP_PATH.iterdir():
        img.unlink()


def CleanAllTaskImage():
    for img in GROUP_TASK_PATH.iterdir():
        img.unlink()


def CleanGroupHelpImage(group_id: int):
    if (file := GROUP_HELP_PATH / f"{group_id}.png").exists():
        file.unlink()


def CleanGroupTaskImage(group_id: int):
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
            for plugin in plugin_manager.GetPluginNameList():
                if not await group_manager.SetPluginEnable(
                    plugin_name=plugin, group_id=event.group_id
                ):
                    count += 1
        else:
            for plugin in plugin_manager.GetPluginNameList():
                if not await group_manager.SetPluginDisable(
                    plugin_name=plugin, group_id=event.group_id
                ):
                    count += 1
        CleanGroupHelpImage(event.group_id)
        await switch.finish(
            f"已{cmd}全部插件"
            + (f"，不包括{count}个全局禁用与无权限插件" if "cmd" == "开启" and count != 0 else "")
        )
    elif param == "全部被动":
        count = 0
        if cmd == "开启":
            for task in task_manager.GetTaskNameList():
                if not await group_manager.SetTaskEnable(
                    task_name=task, group_id=event.group_id
                ):
                    count += 1
        else:
            for task in task_manager.GetTaskNameList():
                if not await group_manager.SetTaskDisable(
                    task_name=task, group_id=event.group_id
                ):
                    count += 1
        CleanGroupTaskImage(event.group_id)
        await switch.finish(
            f"已{cmd}全部被动"
            + (f"，不包括{count}个全局禁用与无权限被动" if "cmd" == "开启" and count != 0 else "")
        )
    if cmd in ("开启被动", "关闭被动") and (name := task_manager.GetTaskName(param)):
        if cmd == "开启被动" and not await group_manager.SetTaskEnable(
            task_name=name, group_id=event.group_id
        ):
            await switch.finish(f"插件 {param} 已被全局禁用或权限不足，无法开启")
        elif cmd == "关闭被动":
            await group_manager.SetTaskDisable(task_name=name, group_id=event.group_id)
        CleanGroupTaskImage(event.group_id)
        await switch.finish(f"已{cmd}群被动：{param}")
    if name := plugin_manager.GetPluginName(param):
        if cmd == "开启" and not await group_manager.SetPluginEnable(
            plugin_name=name, group_id=event.group_id
        ):
            await switch.finish(f"插件 {param} 已被全局禁用或权限不足，无法开启")
        elif cmd == "关闭":
            await group_manager.SetPluginDisable(
                plugin_name=name, group_id=event.group_id
            )
        CleanGroupHelpImage(event.group_id)
        await switch.finish(f"已{cmd}插件：{param}")
    elif name := task_manager.GetTaskName(param):
        if cmd == "开启" and not await group_manager.SetTaskEnable(
            task_name=name, group_id=event.group_id
        ):
            await switch.finish(f"插件 {param} 已被全局禁用或权限不足，无法开启")
        elif cmd == "关闭":
            await group_manager.SetTaskDisable(task_name=name, group_id=event.group_id)
        CleanGroupTaskImage(event.group_id)
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
            for plugin in plugin_manager.GetPluginNameList():
                await plugin_manager.EnablePlugin(plugin_name=plugin)
        else:
            for plugin in plugin_manager.GetPluginNameList():
                await plugin_manager.DisablePlugin(plugin_name=plugin)
        CleanAllHelpImage()
        await switch.finish(f"已{cmd}全部插件")
    elif param == "全部被动":
        if cmd == "全局开启":
            for task in task_manager.GetTaskNameList():
                await task_manager.EnableTask(task_name=task)
        else:
            for task in task_manager.GetTaskNameList():
                await task_manager.DisableTask(task_name=task)
        CleanAllTaskImage()
        await switch.finish(f"已{cmd}全部被动")

    if cmd in ("全局开启被动", "全局关闭被动") and (name := task_manager.GetTaskName(param)):
        if cmd == "全局开启被动":
            await task_manager.EnableTask(task_name=name)
        elif cmd == "全局关闭被动":
            await task_manager.DisableTask(task_name=name)
        CleanAllTaskImage()
        await switch.finish(f"已{cmd}群被动：{param}")
    if name := plugin_manager.GetPluginName(param):
        if cmd == "全局开启":
            await plugin_manager.EnablePlugin(plugin_name=name)
        elif cmd == "全局关闭":
            await plugin_manager.DisablePlugin(plugin_name=name)
        CleanAllHelpImage()
        await switch.finish(f"已{cmd}插件：{param}")
    elif name := task_manager.GetTaskName(param):
        if cmd == "全局开启":
            await task_manager.EnableTask(task_name=name)
        elif cmd == "全局关闭":
            await task_manager.DisableTask(task_name=name)
        CleanAllTaskImage()
        await switch.finish(f"已{cmd}群被动：{param}")
    else:
        await switch.finish(f"插件或群被动 {param} 不存在")
