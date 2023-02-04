from pathlib import Path
import ujson as json
from typing import Union, Dict

from migangbot.core.permission import NORMAL
from migangbot.core.manager import PluginManager, TaskManager
from migangbot.core.exception import FileTypeError
from migangbot.core.utils.file_operation import AsyncSaveData


class GroupManager:
    """ """

    class Group:
        def __init__(self, data: Dict) -> None:
            self.__data = data
            self.permission: int = data["permission"]
            self.bot_status: bool = data["bot_status"]

        def SetBotEnable(self) -> bool:
            if self.bot_status:
                return False
            self.__data["bot_status"] = self.bot_status = True
            return True

        def SetBotDisable(self) -> bool:
            if not self.bot_status:
                return False
            self.__data["bot_status"] = self.bot_status = False
            return True

        def SetPermission(self, permission: int):
            self.__data["permission"] = self.permission = permission

    def __init__(
        self,
        file: Union[Path, str],
        plugin_manager: PluginManager,
        task_manager: TaskManager,
    ) -> None:
        self.__data: Dict[str, Dict] = {}
        self.__group: Dict[int, GroupManager.Group] = {}
        self.__file: Path = Path(file) if isinstance(file, str) else file
        self.__dirty_data: bool = False

        # 交由他俩检测插件是否允许，本类仅仅管理群本身权限与bot启用情况
        self.__plugin_manager: PluginManager = plugin_manager
        self.__task_manager: TaskManager = task_manager

        if file.suffix != ".json":
            raise FileTypeError("群管理模块配置文件必须为json格式！")

        file.parent.mkdir(parents=True, exist_ok=True)
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                self.__data = json.load(f)

        for group in self.__data:
            self.__group[int(group)] = GroupManager.Group(self.__data[group])

    async def Save(self):
        if self.__dirty_data:
            await AsyncSaveData(self.__data, self.__file)
            self.__dirty_data = False

    def __get_group(self, group_id: int):
        group = self.__group.get(group_id)
        if not group:
            self.__data[group_id] = {
                "permission": NORMAL,
                "bot_status": True,
            }
            group = self.__group[group_id] = GroupManager.Group(self.__data[group_id])
            self.__dirty_data = True
        return group

    def CheckGroupPluginStatus(self, plugin_name: str, group_id: int):
        group = self.__get_group(group_id=group_id)
        return group.bot_status and self.__plugin_manager.CheckGroupStatus(
            plugin_name=plugin_name,
            group_id=group_id,
            group_permission=group.permission,
        )

    def CheckGroupTaskStatus(self, task_name: str, group_id: int):
        group = self.__get_group(group_id=group_id)
        return group.bot_status and self.__task_manager.CheckGroupStatus(
            task_name=task_name,
            group_id=group_id,
            group_permission=group.permission,
        )

    def CheckPluginPermission(self, plugin_name: str, group_id: int):
        group = self.__get_group(group_id=group_id)
        return self.__plugin_manager.CheckPermission(
            plugin_name=plugin_name, permission=group.permission
        )

    def CheckTaskPermission(self, task_name: str, group_id: int):
        group = self.__get_group(group_id=group_id)
        return self.__task_manager.CheckPermission(
            task_name=task_name, permission=group.permission
        )

    async def SetPluginEnable(
        self, plugin_name: str, group_id: int
    ):
        group = self.__get_group(group_id=group_id)
        if self.__plugin_manager.CheckPermission(
            plugin_name=plugin_name, permission=group.permission
        ):
            if await self.__plugin_manager.SetGroupEnable(
                plugin_name=plugin_name, group_id=group_id
            ):
                return True
        return False

    async def SetPluginDisable(
        self, plugin_name: str, group_id: int
    ):
        group = self.__get_group(group_id=group_id)
        if self.__plugin_manager.CheckPermission(
            plugin_name=plugin_name, permission=group.permission
        ):
            await self.__plugin_manager.SetGroupDisable(
                plugin_name=plugin_name, group_id=group_id
            )
            return True
        return False

    async def SetTaskEnable(
        self, task_name: str, group_id: int
    ):
        group = self.__get_group(group_id=group_id)
        if self.__task_manager.CheckPermission(
            task_name=task_name, permission=group.permission
        ):
            if await self.__task_manager.SetGroupEnable(
                task_name=task_name, group_id=group_id
            ):
                return True
        return False

    async def SetTaskDisable(
        self, task_name: str, group_id: int
    ):
        group = self.__get_group(group_id=group_id)
        if self.__task_manager.CheckPermission(
            task_name=task_name, permission=group.permission
        ):
            await self.__task_manager.SetGroupDisable(
                task_name=task_name, group_id=group_id
            )
            return True
        return False

    def EnableBot(self, group_id: int) -> bool:
        group = self.__get_group(group_id=group_id)
        if group.SetBotEnable():
            self.__dirty_data = True
            return True
        return False

    def DisableBot(self, group_id: int) -> bool:
        group = self.__get_group(group_id=group_id)
        if group.SetBotDisable():
            self.__dirty_data = True
            return True
        return False

    async def Add(self, group_id: int, auto_save=True):
        self.__get_group(group_id=group_id)
        if auto_save:
            await self.Save()
        else:
            self.__dirty_data = True

    async def Remove(self, group_id: int, auto_save=True):
        if group_id in self.__group:
            del self.__data[str(group_id)]
            del self.__group[group_id]
            if auto_save:
                await self.Save()
            else:
                self.__dirty_data = True
