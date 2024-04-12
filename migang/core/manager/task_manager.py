import asyncio
from pathlib import Path
from typing import Set, Dict, List, Union, Iterable, Optional

import anyio
from pydantic import BaseModel

from migang.core.permission import NORMAL, Permission


class TaskItem:
    """__plugin_task__属性为Iterable[TaskItem]或TaskItem"""

    def __init__(
        self,
        task_name: str,
        name: str,
        default_status: bool = False,
        global_status: bool = True,
        usage: str = None,
        description: str = "",
        permission: Permission = NORMAL,
    ) -> None:
        """TaskItem构造函数，__plugin_task__属性为Iterable[TaskItem]或TaskItem

        Args:
            task_name (str): 任务名
            name (str): 名字
            default_status (bool, optional): 默认状态. Defaults to False.
            global_status (bool, optional): 全局状态. Defaults to True.
            usage (str, optional): 用法. Defaults to None.
            description (str, optional): 任务描述，写在配置文件中免得看不懂. Defaults to "".
            permission (Permission, optional): 所需权限. Defaults to NORMAL.
        """
        self.task_name = task_name
        self.name = name
        self.default_status = default_status
        self.global_status = global_status
        self.usage = usage
        self.description = description
        self.permission = permission


class TaskManager:
    """管理全部任务"""

    class TaskAttr(BaseModel):
        name: str
        permission: Permission
        global_status: bool
        default_status: bool
        enabled_group: Set[int]
        disabled_group: Set[int]
        description: str

    class Task:
        """管理单个任务"""

        def __init__(self, file: Path, usage: str = None) -> None:
            """Task构造函数，管理单个任务

            Args:
                file (Path): 任务对应的配置文件
                usage (str, optional): 用法. Defaults to None.
            """
            self.__data: TaskManager.TaskAttr
            self.__file = file

            self.task_name: str = self.__file.name.removesuffix(".json")
            self.name: str
            self.usage: str = usage
            self.__permission: Permission
            self.__global_status: bool
            self.__default_status: bool
            self.__non_default_group: Set[int]

        async def init(self) -> None:
            """异步初始化Task类"""
            async with await anyio.open_file(self.__file, "r") as f:
                self.__data = TaskManager.TaskAttr.model_validate_json(await f.read())
            self.name: str = self.__data.name
            self.__permission: Permission = self.__data.permission
            self.__global_status: bool = self.__data.global_status
            self.__default_status: bool = self.__data.default_status
            self.__non_default_group: Set[int] = (
                self.__data.disabled_group
                if self.__default_status
                else self.__data.enabled_group
            )

        async def save(self) -> None:
            """保存数据进文件"""
            async with await anyio.open_file(self.__file, "w") as f:
                await f.write(self.__data.model_dump_json(indent=4))

        @property
        def global_status(self) -> bool:
            """全局状态

            Returns:
                bool: 全局状态
            """
            return self.__global_status

        def set_usage(self, usage: Optional[str]) -> None:
            """设置用法

            Args:
                usage (Optional[str]): 用法
            """
            self.usage = usage

        def enable(self):
            """全局启用"""
            self.__data.global_status = self.__global_status = True

        def disable(self):
            """全局禁用"""
            self.__data.global_status = self.__global_status = False

        def check_group_status(
            self, group_id: int, group_permission: Permission
        ) -> bool:
            """检测群是否能调用该任务

            Args:
                group_id (int): 群号
                group_permission (Permission): 群权限

            Returns:
                bool: 若能调用，返回True
            """
            return (
                self.__global_status
                and (group_permission >= self.__permission)
                and (self.__default_status ^ (group_id in self.__non_default_group))
            )

        def check_permission(self, permission: Permission) -> bool:
            """检测权限

            Args:
                permission (Permission): 权限

            Returns:
                bool: 若权限足够，返回True
            """
            return permission >= self.__permission

        def set_group_enable(self, group_id: int) -> bool:
            """在群group_id中启用该任务

            Args:
                group_id (int): 群号

            Returns:
                bool: 若全局禁用则无法启用返回False，反之返回True
            """
            if not self.__global_status:
                return False
            if self.__default_status:
                if group_id in self.__non_default_group:
                    self.__non_default_group.remove(group_id)
                if group_id not in self.__data.enabled_group:
                    self.__data.enabled_group.add(group_id)
            else:
                if group_id not in self.__non_default_group:
                    self.__non_default_group.add(group_id)
                if group_id in self.__data.disabled_group:
                    self.__data.disabled_group.remove(group_id)
            return True

        def set_group_disable(self, group_id: int) -> bool:
            """在群group_id中禁用该任务

            Args:
                group_id (int): 群号

            Returns:
                bool: 返回True
            """
            if self.__default_status:
                if group_id not in self.__non_default_group:
                    self.__non_default_group.add(group_id)
                if group_id in self.__data.enabled_group:
                    self.__data.enabled_group.remove(group_id)
            else:
                if group_id in self.__non_default_group:
                    self.__non_default_group.remove(group_id)
                if group_id not in self.__data.disabled_group:
                    self.__data.disabled_group.add(group_id)
            return True

        def clean_group(self, group_set: Set[int]) -> None:
            """清理配置文件中冗余的群

            Args:
                group_set (Set[int]): 当前有效的群
            """
            self.__non_default_group &= group_set

    def __init__(self, file_path: Path) -> None:
        """TaskManager构造函数，管理全部插件

        Args:
            file_path (Path): 存储插件配置的文件夹名
        """
        self.__file_path = file_path
        self.__file_path.mkdir(exist_ok=True, parents=True)
        self.__task: Dict[str, TaskManager.Task] = {}
        """获取任务task_name对应的Task类
        """
        self.__names: Dict[str, str] = {}
        """建立任务别名到task_name的映射
        """
        self.__files: Optional[Set[str]] = set(
            [file.name for file in self.__file_path.iterdir()]
        )
        """初始化后就销毁，添加新插件时减少系统调用
        """

    async def init(self) -> List[Optional[str]]:
        """异步初始化所有Task类

        Returns:
            List[Optional[str]]: List中项为None时表示无异常，反之为表示异常的字符串
        """
        self.__files = None
        ret = await asyncio.gather(
            *[task.init() for task in self.__task.values()],
            return_exceptions=True,
        )
        for task in self.__task.values():
            self.__names[task.name] = task.task_name
        return ret

    def check_group_status(
        self, task_name: str, group_id: int, group_permission: Permission
    ) -> bool:
        """检测任务task_name是否响应该群，由group_manager调用

        Args:
            task_name (str): 任务名
            group_id (int): 群号
            group_permission (Permission): 群权限

        Returns:
            bool: 若响应，返回True
        """
        return (not (task := self.__task.get(task_name))) or task.check_group_status(
            group_id=group_id, group_permission=group_permission
        )

    def check_permission(self, task_name: str, permission: Permission) -> bool:
        """检测permission的权限能否调用task_name插件

        Args:
            task_name (str): 任务名
            permission (Permission): 权限

        Returns:
            bool: 若权限足够返回True
        """
        return (not (task := self.__task.get(task_name))) or task.check_permission(
            permission=permission
        )

    async def set_group_enable(self, task_name: str, group_id: int) -> bool:
        """启用group_id中的task_name任务

        Args:
            task_name (str): 任务名
            group_id (int): 群号

        Returns:
            bool: 若返回False则表示已被全局禁用，反之返回True
        """
        if (task := self.__task.get(task_name)) and task.set_group_enable(group_id):
            await task.save()
            return True
        return False

    async def set_group_disable(self, task_name: str, group_id: int) -> bool:
        """禁用group_id中的task_name任务

        Args:
            task_name (str): 任务名
            group_id (int): 群号

        Returns:
            bool: 返回True
        """
        if (task := self.__task.get(task_name)) and task.set_group_disable(group_id):
            await task.save()
            return True
        return False

    def check_task(self, name: str) -> bool:
        """检测是否存在task_name的任务

        Args:
            name (str): 任务名

        Returns:
            bool: 若有，返回True
        """
        return name in self.__task

    def get_task_name_list(self) -> Set[str]:
        """获取任务名列表

        Returns:
            Set[str]: 任务名们
        """
        return self.__task.keys()

    def get_task_name(self, name: str) -> Optional[str]:
        """由任务名或别名获取插件名（task_name）

        Args:
            name (str): 任务名或别名

        Returns:
            Optional[str]: 若有返回任务名，反之None
        """
        if name in self.__task:
            return name
        return self.__names.get(name)

    def get_task_list(self) -> Set[Task]:
        """获取管理任务的Task类们

        Returns:
            Set[Plugin]: Task类们
        """
        return self.__task.values()

    def get_task_usage(self, name: str) -> Optional[str]:
        """获取任务帮助，支持task_name与别名

        Args:
            name (str): 任务名或别名

        Returns:
            Optional[str]: 若找不到或该任务没有用法介绍，返回None
        """
        if name not in self.__task and name not in self.__names:
            return None
        if name not in self.__task:
            name = self.__names[name]
        return self.__task[name].usage

    async def clean_group(self, group_list: Union[List[int], Set[int]]) -> None:
        """清理配置文件中冗余的群

        Args:
            group_list (Union[List[int], Set[int]]): 当前有效的群
        """
        group_list = set(group_list)
        for task in self.__task.values():
            task.clean_group(group_list)
        await asyncio.gather(*[task.save() for task in self.__task.values()])

    async def enable_task(self, task_name: str):
        """全局启用任务task_name

        Args:
            task_name (str): 任务名
        """
        task = self.__task.get(task_name)
        if not task:
            return
        task.enable()
        await task.save()

    async def disable_task(self, task_name: str):
        """全局禁用任务task_name

        Args:
            task_name (str): 任务名
        """
        task = self.__task.get(task_name)
        if not task:
            return
        task.disable()
        await task.save()

    def set_task_usage(self, task_name: str, usage: Optional[str]):
        """设定插件task_name的用法

        Args:
            task_name (str): 任务名
            usage (Optional[str]): 用法
        """
        if task_name not in self.__task:
            return
        self.__task[task_name].set_usage(usage=usage)

    async def add(self, task_items: Union[TaskItem, Iterable[TaskItem]]) -> None:
        """添加任务进TaskManager，当task_name.json存在时，仅usage会根据最新确定

        Args:
            task_items (Union[TaskItem, LIterable[TaskItem]]): __plugin_task__的值
        """
        if isinstance(task_items, TaskItem):
            task_items: List[TaskItem] = [task_items]
        for item in task_items:
            file_name = f"{item.task_name}.json"
            if file_name not in self.__files:
                async with await anyio.open_file(
                    self.__file_path / file_name, "w"
                ) as f:
                    await f.write(
                        TaskManager.TaskAttr(
                            name=item.name,
                            permission=item.permission,
                            global_status=True,
                            default_status=item.default_status,
                            enabled_group=set(),
                            disabled_group=set(),
                            description=item.description,
                        ).model_dump_json(indent=4)
                    )
            self.__task[item.task_name] = TaskManager.Task(
                file=self.__file_path / file_name, usage=item.usage
            )

    async def remove(self, task_name: str) -> None:
        """从TaskManager中移除插件

        Args:
            task_name (set): 任务名
        """
        if task_name in self.__task:
            del self.__task[task_name]
            (self.__file_path / f"{task_name}.json").unlink()
