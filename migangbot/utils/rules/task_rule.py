from functools import partial

from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent, PokeNotifyEvent

from migangbot.core.manager import group_manager


def GroupTaskChecker(task_name: str):
    return partial(_GroupTaskChecker, task_name=task_name)


def _GroupTaskChecker(event: Event, task_name: str):
    if type(event) not in (GroupMessageEvent, PokeNotifyEvent):
        return False
    return group_manager.CheckGroupTaskStatus(
        task_name=task_name, group_id=event.group_id
    )
