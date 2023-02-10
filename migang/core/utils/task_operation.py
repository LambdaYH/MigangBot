from migang.core.manager import group_manager


def check_task(group_id: int, task_name: str) -> bool:
    """检查任务是否启用（就是为了少些点东西）

    Args:
        group_id (int): 群名
        task_name (str): 任务名

    Returns:
        bool: 若启用，返回True
    """
    return group_manager.check_group_task_status(task_name=task_name, group_id=group_id)
