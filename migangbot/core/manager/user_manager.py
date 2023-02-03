from pathlib import Path
import ujson as json
from typing import Union, Dict

from migangbot.core.permission import NORMAL
from migangbot.core.manager.plugin_manager import PluginManager
from migangbot.core.exception import FileTypeError
from migangbot.core.utils.file_operation import AsyncSaveData


class UserManager:
    """ """

    class User:
        def __init__(self, data: Dict) -> None:
            self.__data = data
            self.permission: int = data["permission"]

        def SetPermission(self, permission: int):
            self.permission = permission
            self.__data["permission"] = permission

    def __init__(self, file: Union[Path, str], plugin_manager: PluginManager) -> None:
        self.__data: Dict[str, Dict] = {}
        self.__user: Dict[int, UserManager.User] = {}
        self.__file: Path = Path(file) if isinstance(file, str) else file
        self.__dirty_data: bool = False

        self.__plugin_manager = plugin_manager

        if file.suffix != ".json":
            raise FileTypeError("用户管理模块配置文件必须为json格式！")

        file.parent.mkdir(parents=True, exist_ok=True)
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                self.__data = json.load(f)

        for user in self.__data:
            self.__user[int(user)] = UserManager.User(self.__data[user])

    async def Save(self):
        if self.__dirty_data:
            await AsyncSaveData(self.__data, self.__file)
            self.__dirty_data = False

    def __get_user(self, user_id: int):
        user = self.__user.get(user_id)
        if not user:
            self.__data[user_id] = {"permission": NORMAL}
            user = self.__user[user_id] = UserManager.User(self.__data[user_id])
            self.__dirty_data = True
        return user

    def CheckUserPluginStatus(self, plugin_name: str, user_id: int):
        user = self.__get_user(user_id=user_id)
        return self.__plugin_manager.CheckUserStatus(
            plugin_name=plugin_name, user_permission=user.permission
        )

    def CheckPluginPermission(self, plugin_name: str, user_id: int):
        user = self.__get_user(user_id=user_id)
        return self.__plugin_manager.CheckPermission(
            plugin_name=plugin_name, permission=user.permission
        )

    async def Add(self, user_id: int, auto_save=True):
        self.__get_user(user_id=user_id)
        if auto_save:
            await self.Save()
        else:
            self.__dirty_data = True

    async def Remove(self, user_id: int, auto_save=True):
        if user_id in self.__user:
            del self.__data[str(user_id)]
            del self.__user[user_id]
            if auto_save:
                await self.Save()
            else:
                self.__dirty_data = True
