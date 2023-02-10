from typing import Callable
from functools import partial

from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent, PokeNotifyEvent

from migang.core.manager import group_manager


def GroupTaskChecker(task_name: str) -> Callable:
    """返回一个参数为event的任务检测器，检测任务是否能够响应该事件

    Args:
        task_name (str): 任务名

    Returns:
        Callable: 参数为event的任务检测器
    """
    return partial(_group_task_checker, task_name=task_name)


def _group_task_checker(event: Event, task_name: str) -> bool:
    if not hasattr(event, "group_id"):
        return False
    return group_manager.check_group_task_status(
        task_name=task_name, group_id=event.group_id
    )
