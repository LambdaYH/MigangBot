from pathlib import Path
import ujson as json
from typing import Union, Dict

from migangbot.core.permission import NORMAL
from migangbot.core.manager.plugin_manager import PluginManager
from migangbot.core.exception import FileTypeError
from migangbot.core.utils.file_operation import AsyncSaveData


class Group:
    def __init__(self, data: Dict) -> None:
        self.__data = data
        self.__permission: int = data["permission"]
        self.__bot_status: bool = data["bot_status"]

    @property
    def Permission(self) -> int:
        return self.__permission

    @property
    def BotStatus(self):
        return self.__bot_status

    def SetBotEnable(self):
        self.__bot_status = True
        self.__data["bot_status"] = True

    def SetBotDisable(self):
        self.__bot_status = False
        self.__data["bot_status"] = False

    def SetPermission(self, permission: int):
        self.__permission = permission
        self.__data["permission"] = permission


class GroupManager:
    """ """

    def __init__(
        self,
        file: Union[Path, str],
        plugin_manager: PluginManager,
        task_manager: PluginManager,
    ) -> None:
        self.__data: Dict[str, Dict] = {}
        self.__group: Dict[int, Group] = {}
        self.__file: Path = Path(file) if isinstance(file, str) else file

        # 交由他俩检测插件是否允许，本类仅仅管理群本身权限与bot启用情况
        self.__plugin_manager = plugin_manager
        self.__task_manager = task_manager

        if file.suffix != ".json":
            raise FileTypeError("群管理模块配置文件必须为json格式！")

        file.parent.mkdir(parents=True, exist_ok=True)
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                self.__data = json.load(f)

        for group in self.__data:
            self.__group[int(group)] = Group(self.__data[group])

    def CheckGroupPluginStatus(self, plugin_name: str, group_id: int):
        return (group_id not in self.__group) or (
            self.__group[group_id].BotStatus
            and self.__plugin_manager.CheckGroupStatus(
                plugin_name=plugin_name,
                group_id=group_id,
                group_permission=self.__group[group_id].Permission,
            )
        )

    async def Save(self):
        await AsyncSaveData(self.__data, self.__file)

    def CheckGroupTaskStatus(self, plugin_name: str, group_id: int):
        return (group_id not in self.__group) or (
            self.__group[group_id].BotStatus
            and self.__task_manager.CheckGroupStatus(
                plugin_name=plugin_name,
                group_id=group_id,
                group_permission=self.__group[group_id].Permission,
            )
        )

    async def EnableBot(self, group_id: int):
        self.__group[group_id].SetBotEnable()
        await self.Save()

    async def DisableBot(self, group_id: int):
        self.__group[group_id].SetBotDisable()
        await self.Save()

    async def AddGroup(self, group_id: int, auto_save=True):
        if group_id in self.__group:
            return
        self.__data[str(group_id)] = {
            "permission": NORMAL,
            "bot_status": True,
        }
        self.__group[group_id] = Group(self.__data[str(group_id)])
        if auto_save:
            await self.Save()

    async def RemoveGroup(self, group_id: int, auto_save=True):
        if group_id in self.__group:
            del self.__data[str(group_id)]
            del self.__group[group_id]
            if auto_save:
                await self.Save()
