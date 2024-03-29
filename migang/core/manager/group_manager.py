import asyncio
from collections import defaultdict
from typing import Set, Dict, DefaultDict

from tortoise.transactions import in_transaction

from migang.core.models import GroupStatus
from migang.core.permission import NORMAL, Permission
from migang.core.manager.task_manager import TaskManager
from migang.core.manager.plugin_manager import PluginManager


class Group:
    __slots__ = "permission", "bot_status"

    def __init__(self, permission: Permission, bot_status: bool) -> None:
        self.permission = permission
        self.bot_status = bot_status

    def set_bot_enable(self) -> bool:
        """启用群机器人

        Returns:
            bool: 若True，则启用成功，反之则表示处于启用状态
        """
        if self.bot_status:
            return False
        self.bot_status = True
        return True

    def set_bot_disable(self) -> bool:
        """禁用群机器人

        Returns:
            bool: 若True，则禁用成功，反之则表示处于禁用状态
        """
        if not self.bot_status:
            return False
        self.bot_status = False
        return True

    def set_permission(self, permission: Permission):
        """设定群权限

        Args:
            permission (Permission): 新权限
        """
        self.permission = permission


class GroupManager:
    """管理群能否调用插件与任务以及群机器人的状态

    Raises:
        FileTypeError: 找不到记录文件
    """

    def __init__(
        self,
        plugin_manager: PluginManager,
        task_manager: TaskManager,
    ) -> None:
        """GroupManager构造函数，管理群能否调用插件与任务以及群机器人的状态

        Args:
            plugin_manager (PluginManager): 插件管理器
            task_manager (TaskManager): 任务管理器
        """
        self.__group: Dict[int, Group] = {}
        """group_id 对应一个group类
        """
        self.__plugin_manager: PluginManager = plugin_manager
        """管理插件
        """
        self.__task_manager: TaskManager = task_manager
        """管理任务
        """
        self.__save_query: DefaultDict[int, Set[str]] = defaultdict(set)

    async def init(self) -> None:
        """初始化，从数据库中载入"""
        all_groups = await GroupStatus.all()
        for group in all_groups:
            self.__group[group.group_id] = Group(group.permission, group.bot_status)

    async def save(self) -> None:
        """写进数据库"""
        if self.__save_query:
            async with in_transaction() as connection:
                tasks = []
                for group_id, fields in self.__save_query.items():
                    group_status = await GroupStatus.filter(group_id=group_id).first()
                    if not group_status:
                        # 若数据库中没有，创建
                        group_status = GroupStatus(
                            group_id=group_id,
                            permission=self.__group[group_id].permission,
                            bot_status=self.__group[group_id].bot_status,
                        )
                    else:
                        # 更新修改过的项
                        for field in fields:
                            group_status.__setattr__(
                                field, self.__group[group_id].__getattribute__(field)
                            )
                    tasks.append(
                        group_status.save(update_fields=fields, using_db=connection)
                    )
                self.__save_query.clear()
                await asyncio.gather(*tasks)

    def __get_group(self, group_id: int) -> Group:
        """获取group_id对应的Group类，若无，则创建

        Args:
            group_id (int): 群号

        Returns:
            Group: group_id对应的Group类
        """
        group = self.__group.get(group_id)
        if not group:
            group = self.__group[group_id] = Group(permission=NORMAL, bot_status=True)
            self.__save_query[group_id].update()
        return group

    def check_group_plugin_status(self, plugin_name: str, group_id: int) -> bool:
        """检测群group_id是否能调用plugin_name插件，若能，返回True

        Args:
            plugin_name (str): 插件名
            group_id (int): 群号

        Returns:
            bool: 若能调用，返回True
        """
        group = self.__get_group(group_id=group_id)
        return group.bot_status and self.__plugin_manager.check_group_status(
            plugin_name=plugin_name,
            group_id=group_id,
            group_permission=group.permission,
        )

    def check_group_task_status(self, task_name: str, group_id: int) -> bool:
        """检测群group_id是否能调用task_name任务，若能，返回True

        Args:
            task_name (str): 任务名
            group_id (int): 群号

        Returns:
            bool: 若能调用，返回True
        """
        group = self.__get_group(group_id=group_id)
        return group.bot_status and self.__task_manager.check_group_status(
            task_name=task_name,
            group_id=group_id,
            group_permission=group.permission,
        )

    def check_plugin_permission(self, plugin_name: str, group_id: int) -> bool:
        """检测群group_id是否有插件plugin_name的调用权限

        Args:
            plugin_name (str): 插件名
            group_id (int): 群号

        Returns:
            bool: 若有权限，返回True
        """
        group = self.__get_group(group_id=group_id)
        return self.__plugin_manager.check_group_permission(
            plugin_name=plugin_name, permission=group.permission
        )

    def check_task_permission(self, task_name: str, group_id: int) -> bool:
        """检测群group_id是否有任务task_name的调用权限

        Args:
            task_name (str): 任务名
            group_id (int): 群号

        Returns:
            bool: 若有权限，返回True
        """
        group = self.__get_group(group_id=group_id)
        return self.__task_manager.check_permission(
            task_name=task_name, permission=group.permission
        )

    async def set_plugin_enable(self, plugin_name: str, group_id: int) -> bool:
        """启用群group_id的plugin_name插件

        Args:
            plugin_name (str): 插件名
            group_id (int): 群号

        Returns:
            bool: 若启用成功，返回True
        """
        group = self.__get_group(group_id=group_id)
        if self.__plugin_manager.check_group_permission(
            plugin_name=plugin_name, permission=group.permission
        ):
            if await self.__plugin_manager.set_group_enable(
                plugin_name=plugin_name, group_id=group_id
            ):
                return True
        return False

    async def set_plugin_disable(self, plugin_name: str, group_id: int) -> bool:
        """禁用群group_id的plugin_name插件

        Args:
            plugin_name (str): 插件名
            group_id (int): 群号

        Returns:
            bool: 若禁用成功，返回True
        """
        group = self.__get_group(group_id=group_id)
        if self.__plugin_manager.check_group_permission(
            plugin_name=plugin_name, permission=group.permission
        ):
            if await self.__plugin_manager.set_group_disable(
                plugin_name=plugin_name, group_id=group_id
            ):
                return True
        return False

    async def set_task_enable(self, task_name: str, group_id: int):
        """启用群group_id的task_name任务

        Args:
            task_name (str): 任务名
            group_id (int): 群号

        Returns:
            _type_: 若启用成功，返回True
        """
        group = self.__get_group(group_id=group_id)
        if self.__task_manager.check_permission(
            task_name=task_name, permission=group.permission
        ):
            if await self.__task_manager.set_group_enable(
                task_name=task_name, group_id=group_id
            ):
                return True
        return False

    async def set_task_disable(self, task_name: str, group_id: int):
        """禁用群group_id的task_name任务

        Args:
            task_name (str): 任务名
            group_id (int): 群号

        Returns:
            _type_: 若禁用成功，返回True
        """
        group = self.__get_group(group_id=group_id)
        if self.__task_manager.check_permission(
            task_name=task_name, permission=group.permission
        ):
            await self.__task_manager.set_group_disable(
                task_name=task_name, group_id=group_id
            )
            return True
        return False

    def enable_bot(self, group_id: int) -> bool:
        """启用群group_id的机器人

        Args:
            group_id (int): 群号

        Returns:
            bool: 若启用成功，返回True，反之表示已启用
        """
        group = self.__get_group(group_id=group_id)
        if group.set_bot_enable():
            self.__save_query[group_id].add("bot_status")
            return True
        return False

    def disable_bot(self, group_id: int) -> bool:
        """禁用群group_id的机器人

        Args:
            group_id (int): 群号

        Returns:
            bool: 若禁用成功，返回True，反之表示已禁用
        """
        group = self.__get_group(group_id=group_id)
        if group.set_bot_disable():
            self.__save_query[group_id].add("bot_status")
            return True
        return False

    def set_group_permission(self, group_id: int, permission: Permission):
        """设定群权限

        Args:
            group_id (int): 群号
            permission (Permission): 群权限
        """
        group = self.__get_group(group_id=group_id)
        group.set_permission(permission=permission)
        self.__save_query[group_id].add("permission")

    def get_group_permission(self, group_id: int) -> Permission:
        """获取群权限

        Args:
            group_id (int): 群号

        Returns:
            Permission: 群权限
        """
        return self.__get_group(group_id=group_id).permission
