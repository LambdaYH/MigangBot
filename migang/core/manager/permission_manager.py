"""管理用户权限，支持定时管理
"""
import asyncio
import heapq
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Union

import anyio
from pydantic import BaseModel

from migang.core.manager import group_manager, user_manager
from migang.core.permission import Permission


class PermItem(BaseModel):
    expired: datetime
    target_perm: Permission

    def __eq__(self, __o: object) -> bool:
        return self.expired == __o.expired

    def __ne__(self, __o: object) -> bool:
        return self.expired != __o.expired

    def __gt__(self, __o: object) -> bool:
        return self.expired > __o.expired

    def __ge__(self, __o: object) -> bool:
        return self.expired >= __o.expired

    def __lt__(self, __o: object) -> bool:
        return self.expired < __o.expired

    def __le__(self, __o: object) -> bool:
        return self.expired <= __o.expired


class GroupPermItem(PermItem):
    group_id: int


class UserPermItem(PermItem):
    user_id: int


class TinyPriorityQueue(BaseModel):
    """一个勉强能用的优先队列"""

    data: List[Union[GroupPermItem, UserPermItem]] = []
    """一个小顶堆
    """

    def push(self, item: Union[GroupPermItem, UserPermItem]) -> None:
        heapq.heappush(self.data, item)

    def pop(self) -> Union[GroupPermItem, UserPermItem, None]:
        if len(self.data) == 0:
            return None
        return heapq.heappop(self.data)

    def top(self) -> Union[GroupPermItem, UserPermItem, None]:
        if len(self.data) == 0:
            return None
        return self.data[0]

    def empty(self) -> bool:
        return len(self.data) == 0


class PermissionManager:
    """管理权限，可用于设定限时权限"""

    def __init__(self, file: Path) -> None:
        self.__file: Path = file
        if file.exists():
            self.__data: TinyPriorityQueue = TinyPriorityQueue.parse_file(file)
        else:
            self.__data: TinyPriorityQueue = TinyPriorityQueue()
        self.__dirty_data = False
        self.__event: asyncio.Event = asyncio.Event()

    def init(self) -> None:
        """等事件循环出来后启动"""
        asyncio.create_task(self.__permission_setting_task())

    async def save(self) -> None:
        """保存"""
        # 反正每次启动时候都会检查，所以关bot和新添加时候保存就行了
        if self.__dirty_data:
            async with await anyio.open_file(self.__file, "w", encoding="utf-8") as f:
                await f.write(self.__data.json(ensure_ascii=False, indent=4))
            self.__dirty_data = False

    async def __permission_setting_task(self) -> None:
        """定时检查是否需要把权限改回去的后台任务"""
        while True:
            now = datetime.now()
            while not self.__data.empty() and self.__data.top().expired >= now:
                item = self.__data.pop()
                if isinstance(item, GroupPermItem):
                    self.set_group_perm(
                        group_id=item.group_id, permission=item.target_perm
                    )
                else:
                    self.set_user_perm(
                        user_id=item.user_id, permission=item.target_perm
                    )
            self.__event.clear()
            if not self.__data.empty():
                try:
                    await asyncio.wait_for(
                        self.__event.wait,
                        timeout=(self.__data.top().expired - now).total_seconds(),
                    )
                    # 没超时说明被唤醒了
                except TimeoutError:
                    # 超时了就接着去清理
                    pass
            else:
                await self.__event.wait()

    def set_user_perm(
        self,
        user_id: int,
        permission: Permission,
        duration: Union[int, timedelta, None] = None,
    ) -> None:
        """设定用户权限

        Args:
            user_id (int): 用户id
            permission (Permission): _权限
            duration (Union[int, timedelta, None], optional): 时长，当为int时，单位为秒，为None时则永久. Defaults to None.
        """
        if duration is not None:
            if isinstance(duration, int):
                duration = timedelta(seconds=duration)
            self.__data.push(
                UserPermItem(
                    expired=datetime.now() + duration,
                    target_perm=user_manager.get_user_permission(user_id=user_id),
                    user_id=user_id,
                )
            )
            self.__dirty_data = True
            self.__event.set()
        user_manager.set_user_permission(user_id=user_id, permission=permission)

    def set_group_perm(
        self,
        group_id: int,
        permission: Permission,
        duration: Union[int, timedelta, None] = None,
    ) -> None:
        """设定群权限

        Args:
            group_id (int): 群id
            permission (Permission): _权限
            duration (Union[int, timedelta, None], optional): 时长，当为int时，单位为秒，为None时则永久. Defaults to None.
        """
        if duration is not None:
            if isinstance(duration, int):
                duration = timedelta(seconds=duration)
            self.__data.push(
                GroupPermItem(
                    expired=datetime.now() + duration,
                    target_perm=group_manager.get_group_permission(group_id=group_id),
                    group_id=group_id,
                )
            )
            self.__dirty_data = True
            self.__event.set()  # 唤醒
        group_manager.set_group_permission(group_id=group_id, permission=permission)

    def get_user_perm(self, user_id: int) -> Permission:
        """获取用户权限

        Args:
            user_id (int): 用户id

        Returns:
            Permission: 权限
        """
        return user_manager.get_user_permission(user_id=user_id)

    def get_group_perm(self, group_id: int) -> Permission:
        """获取群权限

        Args:
            group_id (int): 群号

        Returns:
            Permission: 权限
        """
        return group_manager.get_group_permission(group_id=group_id)