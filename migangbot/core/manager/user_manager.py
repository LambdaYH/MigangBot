from pathlib import Path
import ujson as json
from typing import Union, Dict

from migangbot.core.permission import NORMAL
from migangbot.core.manager.plugin_manager import PluginManager
from migangbot.core.exception import FileTypeError
from migangbot.core.utils.file_operation import async_save_data


class UserManager:
    """管理用户能否调用插件与任务以及群机器人的状态

    Raises:
        FileTypeError: 找不到记录文件
    """

    class User:
        """管理单个用户，记录用户权限"""

        def __init__(self, data: Dict) -> None:
            """User构造函数

            Args:
                data (Dict): 该用户对应的在Dict中的部分数据
            """
            self.__data = data
            self.permission: int = data["permission"]

        def set_permission(self, permission: int):
            """设定用户权限

            Args:
                permission (int): 新权限
            """
            self.permission = permission
            self.__data["permission"] = permission

    def __init__(self, file: Union[Path, str], plugin_manager: PluginManager) -> None:
        """UserManager构造函数，管理用户能否调用插件与任务以及群机器人的状态

        Args:
            file (Union[Path, str]): 记录文件
            plugin_manager (PluginManager): 插件管理器

        Raises:
            FileTypeError: 找不到记录文件
        """
        self.__data: Dict[str, Dict] = {}
        """总数据，{user_id: {"permission": permission}}
        """
        self.__user: Dict[int, UserManager.User] = {}
        """记录user_id对应的User类
        """
        self.__file: Path = Path(file) if isinstance(file, str) else file
        self.__dirty_data: bool = False
        """若数据被修改了则标记为脏数据
        """

        self.__plugin_manager = plugin_manager
        """管理插件
        """

        if file.suffix != ".json":
            raise FileTypeError("用户管理模块配置文件必须为json格式！")

        file.parent.mkdir(parents=True, exist_ok=True)
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                self.__data = json.load(f)

        for user in self.__data:
            self.__user[int(user)] = UserManager.User(self.__data[user])

    async def save(self) -> None:
        """保存进文件"""
        if self.__dirty_data:
            await async_save_data(self.__data, self.__file)
            self.__dirty_data = False

    def __get_user(self, user_id: int) -> User:
        """获取user_id对应的User类，若无，则创建

        Args:
            user_id (int): 用户id

        Returns:
            User: user_id对应的User类
        """
        user = self.__user.get(user_id)
        if not user:
            self.__data[user_id] = {"permission": NORMAL}
            user = self.__user[user_id] = UserManager.User(self.__data[user_id])
            self.__dirty_data = True
        return user

    def CheckUserPluginStatus(self, plugin_name: str, user_id: int) -> bool:
        """检测用户user_id是否能调用plugin_name插件，若能，返回True

        Args:
            plugin_name (str): 插件名
            user_id (int): 群号

        Returns:
            bool: 若能调用，返回True
        """
        user = self.__get_user(user_id=user_id)
        return self.__plugin_manager.check_user_status(
            plugin_name=plugin_name, user_permission=user.permission
        )

    def check_plugin_permission(self, plugin_name: str, user_id: int) -> bool:
        """检测用户user_id是否有插件plugin_name的调用权限

        Args:
            plugin_name (str): 插件名
            user_id (int): 群号

        Returns:
            bool: 若有权限，返回True
        """
        user = self.__get_user(user_id=user_id)
        return self.__plugin_manager.check_permission(
            plugin_name=plugin_name, permission=user.permission
        )

    async def add(self, user_id: int, auto_save: bool = True) -> None:
        """添加新用户

        Args:
            user_id (int): 用户ID
            auto_save (bool, optional): 是否立刻保存进硬盘. Defaults to True.
        """
        self.__get_user(user_id=user_id)
        if auto_save:
            await self.save()
        else:
            self.__dirty_data = True

    async def remove(self, user_id: int, auto_save: bool = True) -> None:
        """移除用户

        Args:
            user_id (int): 用户ID
            auto_save (bool, optional): 是否立刻保存进硬盘. Defaults to True.
        """
        if user_id in self.__user:
            del self.__data[str(user_id)]
            del self.__user[user_id]
            if auto_save:
                await self.save()
            else:
                self.__dirty_data = True
