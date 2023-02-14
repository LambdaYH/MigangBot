from pathlib import Path
from typing import Union, Dict

import aiofiles
from pydantic import BaseModel

from migang.core.permission import NORMAL, Permission
from migang.core.manager.plugin_manager import PluginManager
from migang.core.exception import FileTypeError


class UserManager:
    """管理用户能否调用插件与任务以及群机器人的状态

    Raises:
        FileTypeError: 找不到记录文件
    """

    class TotalData(BaseModel):
        class User(BaseModel):
            """管理单个用户，记录用户权限"""

            permission: Permission

            def set_permission(self, permission: Permission):
                """设定用户权限

                Args:
                    permission (Permission): 新权限
                """
                permission = permission

        data: Dict[int, User]

    def __init__(self, file: Union[Path, str], plugin_manager: PluginManager) -> None:
        """UserManager构造函数，管理用户能否调用插件与任务以及群机器人的状态

        Args:
            file (Union[Path, str]): 记录文件
            plugin_manager (PluginManager): 插件管理器

        Raises:
            FileTypeError: 找不到记录文件
        """
        self.__data: UserManager.TotalData
        """保存到文件时候用的
        """
        self.__user: Dict[int, UserManager.TotalData.User]
        """记录user_id对应的User类
        """
        self.__file: Path = Path(file) if isinstance(file, str) else file
        self.__dirty_data: bool = False
        """若数据被修改了则标记为脏数据
        """

        self.__plugin_manager = plugin_manager
        """管理插件
        """

        if self.__file.suffix != ".json":
            raise FileTypeError("用户管理模块配置文件必须为json格式！")

        self.__file.parent.mkdir(parents=True, exist_ok=True)
        if self.__file.exists():
            self.__data = UserManager.TotalData.parse_file(self.__file)
        else:
            self.__data = UserManager.TotalData(data={})
        self.__user = self.__data.data

    async def save(self) -> None:
        """保存进文件"""
        if self.__dirty_data:
            async with aiofiles.open(self.__file, "w", encoding="utf-8") as f:
                await f.write(self.__data.json(ensure_ascii=False, indent=4))
            self.__dirty_data = False

    def __get_user(self, user_id: int) -> TotalData.User:
        """获取user_id对应的User类，若无，则创建

        Args:
            user_id (int): 用户id

        Returns:
            User: user_id对应的User类
        """
        user = self.__user.get(user_id)
        if not user:
            user = self.__user[user_id] = UserManager.TotalData.User(permission=NORMAL)
            self.__dirty_data = True
        return user

    def check_user_plugin_status(self, plugin_name: str, user_id: int) -> bool:
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
        return self.__plugin_manager.check_user_permission(
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
            del self.__user[user_id]
            if auto_save:
                await self.save()
            else:
                self.__dirty_data = True
