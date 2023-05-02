from typing import Iterable

from nonebot.log import logger

from migang.core.permission import NORMAL
from migang.core.manager import TaskItem, task_manager

from .utils import get_plugin_list


async def init_plugin_task():
    plugins = get_plugin_list()
    count = 0
    for plugin in plugins:
        if not hasattr(plugin.module, "__plugin_task__"):
            continue
        permission = (
            plugin.module.__getattribute__("__plugin_perm__")
            if hasattr(plugin.module, "__plugin_perm__")
            else NORMAL
        )
        task_items: Iterable[TaskItem] = plugin.module.__getattribute__(
            "__plugin_task__"
        )
        if isinstance(task_items, TaskItem):
            task_items = (task_items,)
        try:
            for item in task_items:
                if item.permission is None:
                    item.permission = permission
            await task_manager.add(task_items)
        except Exception as e:
            logger.error(f"无法将插件 {plugin.name} 中的任务加入任务控制：{e}")
    for i, e in enumerate(await task_manager.init()):
        if e:
            logger.error(f"无法将插件 {plugins[i].name} 中的任务加入任务控制：{e}")
        else:
            count += 1
    logger.info(f"已成功将 {len(task_manager.get_task_name_list())} 个任务加入任务控制")
