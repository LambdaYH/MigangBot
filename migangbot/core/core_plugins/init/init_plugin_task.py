from typing import List

from nonebot.log import logger

from migangbot.core.manager import task_manager, TaskItem
from migangbot.core.permission import NORMAL

from .utils import GetPluginList


async def init_plugin_task():
    plugins = GetPluginList()
    count = 0
    for plugin in plugins:
        if not hasattr(plugin.module, "__plugin_task__"):
            continue
        permission = (
            plugin.module.__getattribute__("__plugin_perm__")
            if hasattr(plugin.module, "__plugin_perm__")
            else NORMAL
        )
        task_items: List[TaskItem] = plugin.module.__getattribute__("__plugin_task__")
        if type(task_items) is TaskItem:
            task_items = [task_items]
        try:
            for item in task_items:
                if item.permission is None:
                    item.permission = permission
            await task_manager.Add(task_items)
        except Exception as e:
            logger.error(f"无法将插件 {plugin.name} 中的被动加入被动控制：{e}")
    for i, e in enumerate(await task_manager.Init()):
        if e:
            logger.error(f"无法将插件 {plugins[i].name} 中的被动加入被动控制：{e}")
        else:
            count += 1
    logger.info(f"已成功将 {len(task_manager.GetTaskNameList())} 个被动加入被动控制")
