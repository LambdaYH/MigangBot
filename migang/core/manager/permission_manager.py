"""管理用户权限，支持定时管理
"""
import heapq
import asyncio
from pathlib import Path
from typing import Dict, List, Union
from datetime import datetime, timedelta

import anyio
from pydantic import BaseModel

from migang.core.permission import Permission
from migang.core.manager.user_manager import UserManager
from migang.core.manager.group_manager import GroupManager


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

    def heapify(self):
        """O(n)"""
        heapq.heapify(self.data)


class PermissionManager:
    """管理权限，可用于设定限时权限"""

    def __init__(
        self, file: Path, user_manager: UserManager, group_manager: GroupManager
    ) -> None:
        self.__file: Path = file
        if file.exists():
            self.__data: TinyPriorityQueue = TinyPriorityQueue.parse_file(file)
        else:
            self.__data: TinyPriorityQueue = TinyPriorityQueue()
        self.__group_data: Dict[int, GroupPermItem] = {}
        self.__user_data: Dict[int, UserPermItem] = {}
        """用来检测有没有重复添加
        """
        for item in self.__data.data:
            if isinstance(item, GroupPermItem):
                self.__group_data[item.group_id] = item
            else:
                self.__user_data[item.user_id] = item

        self.__dirty_data = False
        self.__user_manager: UserManager = user_manager
        self.__group_manager: GroupManager = group_manager
        self.__event: asyncio.Event = asyncio.Event()

    def init(self) -> None:
        """等事件循环出来后启动"""
        asyncio.create_task(self.__permission_setting_task())

    async def save(self) -> None:
        """保存"""
        # 反正每次启动时候都会检查，所以关bot和新添加时候保存就行了
        if self.__dirty_data:
            async with await anyio.open_file(self.__file, "w", encoding="utf-8") as f:
                await f.write(self.__data.model_dump_json(ensure_ascii=False, indent=4))
            self.__dirty_data = False

    async def __permission_setting_task(self) -> None:
        """定时检查是否需要把权限改回去的后台任务"""
        while True:
            now = datetime.now()
            while not self.__data.empty() and self.__data.top().expired < now:
                item = self.__data.pop()
                if isinstance(item, GroupPermItem):
                    del self.__group_data[item.group_id]
                    self.__group_manager.set_group_permission(
                        group_id=item.group_id, permission=item.target_perm
                    )
                else:
                    del self.__user_data[item.user_id]
                    self.__user_manager.set_user_permission(
                        user_id=item.user_id, permission=item.target_perm
                    )
                self.__dirty_data = True
            self.__event.clear()
            if not self.__data.empty():
                try:
                    await asyncio.wait_for(
                        self.__event.wait(),
                        timeout=max(
                            (self.__data.top().expired - now).total_seconds(), 0.1
                        ),
                    )
                    # 没超时说明被唤醒了
                except asyncio.TimeoutError:
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
            if user_id in self.__user_data:
                self.__user_data[user_id].expired = datetime.now() + duration
                self.__data.heapify()
            else:
                item = UserPermItem(
                    expired=datetime.now() + duration,
                    target_perm=self.__user_manager.get_user_permission(
                        user_id=user_id
                    ),
                    user_id=user_id,
                )
                self.__user_data[user_id] = item
                self.__data.push(item)
            self.__user_manager.set_user_permission(
                user_id=user_id, permission=permission
            )
            self.__event.set()
            self.__dirty_data = True
        # 若已有记录，立刻清除记录
        else:
            if user_id in self.__user_data:
                user = self.__user_data[user_id]
                user.expired = datetime.now()
                user.target_perm = permission
                self.__data.heapify()
                self.__event.set()
                self.__dirty_data = True
            else:
                self.__user_manager.set_user_permission(
                    user_id=user_id, permission=permission
                )

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
            if group_id in self.__group_data:
                self.__group_data[group_id].expired = datetime.now() + duration
                self.__data.heapify()
            else:
                item = GroupPermItem(
                    expired=datetime.now() + duration,
                    target_perm=self.__group_manager.get_group_permission(
                        group_id=group_id
                    ),
                    group_id=group_id,
                )
                self.__group_data[group_id] = item
                self.__data.push(item)
            self.__group_manager.set_group_permission(
                group_id=group_id, permission=permission
            )
            self.__event.set()  # 唤醒
            self.__dirty_data = True
        else:
            if group_id in self.__group_data:
                group = self.__group_data[group_id]
                group.expired = datetime.now()
                group.target_perm = permission
                self.__data.heapify()
                self.__event.set()
                self.__dirty_data = True
            else:
                self.__group_manager.set_group_permission(
                    group_id=group_id, permission=permission
                )

    def get_user_perm(self, user_id: int) -> Permission:
        """获取用户权限

        Args:
            user_id (int): 用户id

        Returns:
            Permission: 权限
        """
        return self.__user_manager.get_user_permission(user_id=user_id)

    def get_group_perm(self, group_id: int) -> Permission:
        """获取群权限

        Args:
            group_id (int): 群号

        Returns:
            Permission: 权限
        """
        return self.__group_manager.get_group_permission(group_id=group_id)
