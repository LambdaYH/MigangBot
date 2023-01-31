from typing import Tuple

from nonebot.log import logger
from nonebot.params import Command, CommandArg
from nonebot import Driver, get_driver, on_command
from nonebot.adapters.onebot.v11 import GROUP_ADMIN, Message, GroupMessageEvent
from nonebot.plugin import get_loaded_plugins

from migangbot.core.manager import plugin_manager, group_manager
from migangbot.core.permission import NORMAL

driver: Driver = get_driver()

switch = on_command(
    "开启", aliases={"关闭"}, priority=1, block=True, permission=GROUP_ADMIN
)


@switch.handle()
async def _(
    event: GroupMessageEvent,
    cmd: Tuple[str, ...] = Command(),
    arg: Message = CommandArg(),
):
    await group_manager.AddGroup(group_id=event.group_id, auto_save=True)
    cmd = cmd[0]
    param = arg.extract_plain_text().strip()
    if not param:
        await switch.finish()
    if param == "全部插件":
        count = 0
        if cmd == "开启":
            for plugin in plugin_manager.GetPluginList():
                if not await plugin_manager.SetGroupEnable(
                    plugin_name=plugin, group_id=event.group_id, auto_save=False
                ):
                    count += 1
        else:
            for plugin in plugin_manager.GetPluginList():
                if not await plugin_manager.SetGroupDisable(
                    plugin_name=plugin, group_id=event.group_id, auto_save=False
                ):
                    count += 1
        await plugin_manager.Save()
        await switch.finish(
            f"已{cmd}全部插件"
            + (f"，不包括{count}个全局禁用插件" if "cmd" == "开启" and count != 0 else "")
        )
    if name := plugin_manager.GetPluginName(param):
        if cmd == "开启" and not await plugin_manager.SetGroupEnable(
            plugin_name=name, group_id=event.group_id
        ):
            await switch.finish(f"插件 {param} 已被全局禁用，无法开启")
        elif cmd == "关闭":
            await plugin_manager.SetGroupDisable(
                plugin_name=name, group_id=event.group_id
            )
        await switch.finish(f"已{cmd}插件：{param}")
    else:
        await switch.finish(f"插件 {param} 不存在")
