from pathlib import Path
import ujson as json
from typing import Union, Dict

from migangbot.core.permission import NORMAL
from migangbot.core.manager import PluginManager, TaskManager
from migangbot.core.exception import FileTypeError
from migangbot.core.utils.file_operation import async_save_data


class GroupManager:
    """管理群能否调用插件与任务以及群机器人的状态

    Raises:
        FileTypeError: 找不到记录文件
    """

    class Group:
        """管理单个群，记录本群权限以及机器人状态"""

        def __init__(self, data: Dict) -> None:
            """Group构造函数

            Args:
                data (Dict): 该群对应的在Dict中的部分数据
            """
            self.__data = data
            self.permission: int = data["permission"]
            self.bot_status: bool = data["bot_status"]

        def set_bot_enable(self) -> bool:
            """启用群机器人

            Returns:
                bool: 若True，则启用成功，反之则表示处于启用状态
            """
            if self.bot_status:
                return False
            self.__data["bot_status"] = self.bot_status = True
            return True

        def set_bot_disable(self) -> bool:
            """禁用群机器人

            Returns:
                bool: 若True，则禁用成功，反之则表示处于禁用状态
            """
            if not self.bot_status:
                return False
            self.__data["bot_status"] = self.bot_status = False
            return True

        def set_permission(self, permission: int):
            """设定群权限

            Args:
                permission (int): 新权限
            """
            self.__data["permission"] = self.permission = permission

    def __init__(
        self,
        file: Union[Path, str],
        plugin_manager: PluginManager,
        task_manager: TaskManager,
    ) -> None:
        """GroupManager构造函数，管理群能否调用插件与任务以及群机器人的状态

        Args:
            file (Union[Path, str]): 记录文件
            plugin_manager (PluginManager): 插件管理器
            task_manager (TaskManager): 任务管理器

        Raises:
            FileTypeError: 找不到记录文件
        """
        self.__data: Dict[str, Dict] = {}
        """总数据，{group_id: {"permission": permission, "bot_status": status}}
        """
        self.__group: Dict[int, GroupManager.Group] = {}
        """记录group_id对应的Group类
        """
        self.__file: Path = Path(file) if isinstance(file, str) else file
        self.__dirty_data: bool = False
        """若数据被修改了则标记为脏数据
        """

        self.__plugin_manager: PluginManager = plugin_manager
        """管理插件
        """
        self.__task_manager: TaskManager = task_manager
        """管理任务
        """

        if file.suffix != ".json":
            raise FileTypeError("群管理模块配置文件必须为json格式！")

        file.parent.mkdir(parents=True, exist_ok=True)
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                self.__data = json.load(f)

        for group in self.__data:
            self.__group[int(group)] = GroupManager.Group(self.__data[group])

    async def save(self) -> None:
        """保存进文件"""
        if self.__dirty_data:
            await async_save_data(self.__data, self.__file)
            self.__dirty_data = False

    def __get_group(self, group_id: int) -> Group:
        """获取group_id对应的Group类，若无，则创建

        Args:
            group_id (int): 群号

        Returns:
            Group: group_id对应的Group类
        """
        group = self.__group.get(group_id)
        if not group:
            self.__data[group_id] = {
                "permission": NORMAL,
                "bot_status": True,
            }
            group = self.__group[group_id] = GroupManager.Group(self.__data[group_id])
            self.__dirty_data = True
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
        return self.__plugin_manager.check_permission(
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
        if self.__plugin_manager.check_permission(
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
        if self.__plugin_manager.check_permission(
            plugin_name=plugin_name, permission=group.permission
        ):
            await self.__plugin_manager.set_group_disable(
                plugin_name=plugin_name, group_id=group_id
            )
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
            self.__dirty_data = True
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
            self.__dirty_data = True
            return True
        return False

    async def add(self, group_id: int, auto_save: bool = True) -> None:
        """添加新群

        Args:
            group_id (int): 群号
            auto_save (bool, optional): 是否立刻保存进硬盘. Defaults to True.
        """
        self.__get_group(group_id=group_id)
        if auto_save:
            await self.save()
        else:
            self.__dirty_data = True

    async def remove(self, group_id: int, auto_save: bool = True) -> None:
        """移除群

        Args:
            group_id (int): 群号
            auto_save (bool, optional): 是否立刻保存进硬盘. Defaults to True.
        """
        if group_id in self.__group:
            del self.__data[str(group_id)]
            del self.__group[group_id]
            if auto_save:
                await self.save()
            else:
                self.__dirty_data = True