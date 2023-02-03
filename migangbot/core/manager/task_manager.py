import asyncio
from pathlib import Path
from typing import Union, Dict, Set, List, Optional, Any

from migangbot.core.permission import NORMAL
from migangbot.core.utils.file_operation import AsyncLoadData, AsyncSaveData


class TaskItem:
    def __init__(
        self,
        task_name: str,
        name: str,
        default_status: bool = False,
        global_status: bool = True,
        usage: str = None,
        description: str = "",
        permission: int = NORMAL,
    ) -> None:
        self.task_name = task_name
        self.name = name
        self.default_status = default_status
        self.global_status = global_status
        self.usage = usage
        self.description = description
        self.permission = permission


class TaskManager:
    class Task:
        def __init__(self, file: Path, usage: str = None) -> None:
            # 数据
            self.__data: Dict[str, Any]
            self.__file = file

            # 属性
            self.task_name: str = self.__file.name.removesuffix(".json")
            self.name: str
            self.usage: str = usage
            self.__permission: int
            # 全局禁用状态
            self.__global_status: bool
            # 插件默认状态
            self.__default_status: bool
            # 快速查找用
            self.__non_default_group: Set[int]
            # 保存入配置文件用，修改时需要2倍修改量
            self.__enabled_group: List[int]
            self.__disabled_group: List[int]

        async def Init(self) -> None:
            self.__data = await AsyncLoadData(self.__file)
            self.name: str = self.__data["name"]
            self.__permission: int = self.__data["permission"]
            self.__global_status: bool = self.__data["global_status"]
            self.__default_status: bool = self.__data["default_status"]
            self.__non_default_group: Set[int] = (
                set(self.__data["disbled_group"])
                if self.__default_status
                else set(self.__data["enabled_group"])
            )
            self.__enabled_group: List[int] = self.__data["enabled_group"]
            self.__disabled_group: List[int] = self.__data["disbled_group"]

        async def Save(self) -> None:
            await AsyncSaveData(self.__data, self.__file)

        @property
        def global_status(self):
            return self.__global_status

        def SetUsage(self, usage: Optional[str]) -> None:
            self.usage = usage

        def Enable(self):
            self.__data["global_status"] = self.__global_status = True

        def Disable(self):
            self.__data["global_status"] = self.__global_status = False

        def CheckGroupStatus(self, group_id: int, group_permission: int) -> bool:
            return (
                self.__global_status
                and (group_permission >= self.__permission)
                and (self.__default_status ^ (group_id in self.__non_default_group))
            )

        def CheckPermission(self, permission: int) -> bool:
            return permission >= self.__permission

        def SetGroupEnable(self, group_id: int) -> bool:
            if not self.__global_status:
                return False
            if self.__default_status:
                if group_id in self.__non_default_group:
                    self.__non_default_group.remove(group_id)
                    self.__disabled_group.remove(group_id)
                if group_id not in self.__enabled_group:
                    self.__enabled_group.append(group_id)
            else:
                if group_id not in self.__non_default_group:
                    self.__non_default_group.add(group_id)
                    self.__enabled_group.append(group_id)
                if group_id in self.__disabled_group:
                    self.__disabled_group.remove(group_id)
            return True

        def SetGroupDisable(self, group_id: int) -> bool:
            if self.__default_status:
                if group_id not in self.__non_default_group:
                    self.__non_default_group.add(group_id)
                    self.__disabled_group.append(group_id)
                if group_id in self.__enabled_group:
                    self.__enabled_group.remove(group_id)
            else:
                if group_id in self.__non_default_group:
                    self.__non_default_group.remove(group_id)
                    self.__enabled_group.remove(group_id)
                if group_id not in self.__disabled_group:
                    self.__disabled_group.append(group_id)
            return True

        def CleanGroup(self, group_set: Set[int]):
            self.__non_default_group &= group_set
            if self.__default_status:
                self.__disabled_group.clear()
                self.__disabled_group += list(self.__non_default_group)
            else:
                self.__enabled_group.clear()
                self.__enabled_group += list(self.__non_default_group)

    def __init__(self, file_path: Path) -> None:
        self.__file_path = file_path
        self.__file_path.mkdir(exist_ok=True, parents=True)
        self.__task: Dict[str, TaskManager.Task] = {}  # 用于管理插件
        self.__names: Dict[str, str] = {}
        task_files = self.__file_path.iterdir()
        for task_file in task_files:
            if task_file.suffix == ".json":
                task_name = task_file.name.removesuffix(".json")
                self.__task[task_name]: TaskManager.Task = TaskManager.Task(
                    file=task_file
                )

    async def Init(self):
        ret = await asyncio.gather(
            *[task.Init() for task in self.__task.values()],
            return_exceptions=True,
        )
        for task in self.__task.values():
            self.__names[task.name] = task.task_name
        return ret

    def CheckGroupStatus(
        self, task_name: str, group_id: int, group_permission: int
    ) -> bool:
        """
        检查插件是否响应
        若插件不受管理，则默认响应
        """
        return (not (task := self.__task.get(task_name))) or task.CheckGroupStatus(
            group_id=group_id, group_permission=group_permission
        )

    def CheckPermission(self, task_name: str, permission: int) -> bool:
        return (not (task := self.__task.get(task_name))) or task.CheckPermission(
            permission=permission
        )

    async def SetGroupEnable(self, task_name: str, group_id: int) -> bool:
        if (task := self.__task.get(task_name)) and task.SetGroupEnable(group_id):
            await task.Save()
            return True
        return False

    async def SetGroupDisable(self, task_name: str, group_id: int) -> bool:
        if (task := self.__task.get(task_name)) and task.SetGroupDisable(group_id):
            await task.Save()
            return True
        return False

    def CheckTask(self, name: str) -> bool:
        """
        仅支持插件名
        """
        return name in self.__task

    def GetTaskNameList(self) -> Set[str]:
        return self.__task.keys()

    def GetTaskName(self, name: str) -> Optional[str]:
        if name in self.__task:
            return name
        return self.__names.get(name)

    def GetTaskList(self) -> Set[Task]:
        return self.__task.values()

    def GetTaskUsage(self, name: str) -> Optional[str]:
        """
        获取插件帮助，支持模块名与别名
        """
        if name not in self.__task and name not in self.__names:
            return None
        if name not in self.__task:
            name = self.__names[name]
        return self.__task[name].usage

    async def CleanGroup(self, group_list: Union[List[int], Set[int]]) -> None:
        group_list = set(group_list)
        for task in self.__task.values():
            task.CleanGroup(group_list)
        await asyncio.gather(*[task.Save() for task in self.__task.values()])

    async def EnableTask(self, task_name: str):
        task = self.__task.get(task_name)
        if not task:
            return
        task.Enable()
        await task.Save()

    async def DisableTask(self, task_name: str):
        task = self.__task.get(task_name)
        if not task:
            return
        task.Disable()
        await task.Save()

    def SetTaskUsage(self, task_name: str, usage: Optional[str]):
        if task_name not in self.__task:
            return
        self.__task[task_name].SetUsage(usage=usage)

    async def Add(self, task_items: Union[TaskItem, List[TaskItem]]) -> None:
        if type(task_items) is TaskItem:
            task_items: List[TaskItem] = [task_items]
        for item in task_items:
            if item.task_name not in self.__task:
                await AsyncSaveData(
                    {
                        "name": item.name,
                        "permission": item.permission,
                        "global_status": True,
                        "default_status": item.default_status,
                        "enabled_group": [],
                        "disbled_group": [],
                        "_description": item.description,
                    },
                    self.__file_path / f"{item.task_name}.json",
                )
                self.__task[item.task_name] = TaskManager.Task(
                    file=self.__file_path / f"{item.task_name}.json", usage=item.usage
                )
            else:
                self.__task[item.task_name].SetUsage(usage=item.usage)

    async def Remove(self, task_name: str) -> None:
        if task_name in self.__task:
            del self.__task[task_name]
            (self.__file_path / f"{task_name}.json").unlink()
