import asyncio
from collections import defaultdict
from typing import Set, Dict, DefaultDict

from tortoise.transactions import in_transaction

from migang.core.models import UserStatus
from migang.core.permission import NORMAL, Permission
from migang.core.manager.plugin_manager import PluginManager


class User:
    __slots__ = "permission"

    def __init__(self, permission: Permission) -> None:
        self.permission = permission

    def set_permission(self, permission: Permission):
        """设定用户权限

        Args:
            permission (Permission): 新权限
        """
        self.permission = permission


class UserManager:
    """管理用户能否调用插件与任务以及群机器人的状态

    Raises:
        FileTypeError: 找不到记录文件
    """

    def __init__(self, plugin_manager: PluginManager) -> None:
        """UserManager构造函数，管理用户能否调用插件与任务以及群机器人的状态

        Args:
            plugin_manager (PluginManager): 插件管理器
        """
        self.__user: Dict[int, User] = {}
        """记录user_id对应的User类
        """

        self.__plugin_manager = plugin_manager
        """管理插件
        """
        self.__save_query: DefaultDict[int, Set[str]] = defaultdict(set)

    async def init(self) -> None:
        """初始化，从数据库中载入"""
        all_users = await UserStatus.all()
        for user in all_users:
            self.__user[user.user_id] = User(permission=user.permission)

    async def save(self) -> None:
        """写进数据库"""
        if self.__save_query:
            async with in_transaction() as connection:
                tasks = []
                for user_id, fields in self.__save_query.items():
                    user_status = await UserStatus.filter(user_id=user_id).first()
                    if not user_status:
                        # 若数据库中没有，创建
                        user_status = UserStatus(
                            user_id=user_id, permission=self.__user[user_id].permission
                        )
                    else:
                        # 更新修改过的项
                        for field in fields:
                            user_status.__setattr__(
                                field, self.__user[user_id].__getattribute__(field)
                            )
                    tasks.append(
                        user_status.save(update_fields=fields, using_db=connection)
                    )
                self.__save_query.clear()
                await asyncio.gather(*tasks)

    def __get_user(self, user_id: int) -> User:
        """获取user_id对应的User类，若无，则创建

        Args:
            user_id (int): 用户id

        Returns:
            User: user_id对应的User类
        """
        user = self.__user.get(user_id)
        if not user:
            user = self.__user[user_id] = User(permission=NORMAL)
            self.__save_query[user_id].update()
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

    def set_user_permission(self, user_id: int, permission: Permission):
        """设定用户权限

        Args:
            user_id (int): 用户id
            permission (Permission): 权限
        """
        user = self.__get_user(user_id=user_id)
        user.set_permission(permission=permission)
        self.__save_query[user_id].add("permission")

    def get_user_permission(self, user_id: int) -> Permission:
        """获取用户权限

        Args:
            user_id (int): 用户id

        Returns:
            Permission: 权限
        """
        return self.__get_user(user_id=user_id).permission
