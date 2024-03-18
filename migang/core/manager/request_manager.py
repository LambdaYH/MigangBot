"""管理各类请求
"""
from pathlib import Path
from datetime import datetime
from typing import List, Optional

import anyio
from nonebot.log import logger
from pydantic import BaseModel
from nonebot.adapters.onebot.v11 import Bot, ActionFailed


class GroupRequest(BaseModel):
    group_name: Optional[str]
    group_id: int
    user_name: Optional[str]
    user_id: int
    sex: Optional[str]
    age: Optional[int]
    comment: str
    flag: str
    time: datetime


class FriendRequest(BaseModel):
    user_name: Optional[str]
    user_id: int
    sex: Optional[str]
    age: Optional[int]
    comment: str
    flag: str
    time: datetime


class Requests(BaseModel):
    group_request: List[GroupRequest] = []
    friend_request: List[FriendRequest] = []


class RequestManager:
    def __init__(self, file: Path) -> None:
        self.__file = file
        self.__data: Requests
        try:
            with self.__file.open("r", encoding="utf-8") as f:
                self.__data = Requests.model_validate_json(f.read())
        except FileNotFoundError:
            self.__data = Requests()

    async def save(self) -> None:
        async with await anyio.open_file(self.__file, "w", encoding="utf-8") as f:
            await f.write(self.__data.model_dump_json(ensure_ascii=False, indent=4))

    async def add(
        self,
        user_name: Optional[str],
        user_id: int,
        sex: Optional[str],
        age: Optional[int],
        comment: str,
        flag: str,
        time: datetime,
        group_name: Optional[str] = None,
        group_id: Optional[int] = None,
    ) -> None:
        """添加一个请求

        Args:
            user_name (str): 用户名
            user_id (int): 用户id
            sex (str): 性别
            age (int): 年龄
            comment (str): 附加
            flag (str): flag
            time (datetime): 时间
            group_name (Optional[str], optional): 群名. Defaults to None.
            group_id (Optional[int], optional): 群id. Defaults to None.
        """
        if not group_id:
            self.__data.friend_request.append(
                FriendRequest(
                    user_name=user_name,
                    user_id=user_id,
                    sex=sex,
                    age=age,
                    comment=comment,
                    flag=flag,
                    time=time,
                )
            )
        else:
            self.__data.group_request.append(
                GroupRequest(
                    group_name=group_name,
                    group_id=group_id,
                    user_name=user_name,
                    user_id=user_id,
                    sex=sex,
                    age=age,
                    comment=comment,
                    flag=flag,
                    time=time,
                )
            )
        await self.save()

    def remove(self, id_: int, type_: str) -> bool:
        """移除一个请求

        Args:
            id_ (int): 在list中的下标
            type_ (str): group或者friend

        Returns:
            bool: 如果存在该id返回True
        """
        target = (
            self.__data.group_request
            if type_ == "group"
            else self.__data.friend_request
        )
        if id_ >= len(target):
            return False
        del target[id_]
        return True

    async def reset(self, type_: Optional[str]):
        """重置

        Args:
            type_ (Optional[str]): 为None时清空全部，为group时...
        """
        if type_ is None:
            self.__data = Requests()
        elif type_ == "group":
            self.__data.group_request = []
        else:
            self.__data.friend_request = []

        await self.save()

    async def __handle_request(
        self, bot: Bot, id_: int, type_: str, approve: bool, reason: str = ""
    ) -> str:
        """处理请求

        Args:
            bot (Bot): bot
            id (int): 在list中的id
            type_ (str): group 或 friend
            approve (bool): 是否同意
            reason (str, optional): 拒绝群时才有用的理由. Defaults to "".

        Returns:
            str: _description_
        """
        target = (
            self.__data.group_request
            if type_ == "group"
            else self.__data.friend_request
        )
        if id_ >= len(target):
            return f"请输入 0~{len(target) - 1} 之间的id！"
        request = target[id_]
        try:
            if type_ == "group":
                await bot.set_group_add_request(
                    flag=request.flag, sub_type="invite", approve=approve, reason=reason
                )
            else:
                await bot.set_friend_add_request(flag=request.flag, approve=approve)
        except ActionFailed:
            logger.info(
                f"无法{'同意' if approve else '拒绝'}id为{id_}的{'入群' if type_=='group' else '好友'}请求，或许该请求已失效：\n{request.model_dump_json(ensure_ascii=False,indent=4)}"
            )
            del target[id_]
            await self.save()
            return f"无法{'同意' if approve else '拒绝'}id为{id_}的{'入群' if type_=='group' else '好友'}请求，或许该请求已失效"
        logger.info(
            f"已{'同意' if approve else '拒绝'}请求：\n{request.model_dump_json(ensure_ascii=False,indent=4)}"
        )
        del target[id_]
        await self.save()
        if type_ == "group":
            return f"已{'同意' if approve else '拒绝'}群 {request.group_name}({request.group_id}) 的入群请求"
        else:
            return f"已{'同意' if approve else '拒绝'}用户 {request.user_name}({request.user_id}) 的好友请求"

    async def approve(self, bot: Bot, id_: int, type_: str) -> str:
        """同意请求

        Args:
            bot (Bot): bot
            id_ (int): id
            type_ (str): group或friend

        Returns:
            str: 提示语
        """
        return await self.__handle_request(bot=bot, id_=id_, type_=type_, approve=True)

    async def reject(self, bot: Bot, id_: int, type_: str, reason: str = "") -> str:
        """_summary_

        Args:
            bot (Bot): bot
            id_ (int): id
            type_ (str): group或friend
            reason (str, optional): 拒绝群聊时才有用的. Defaults to "".

        Returns:
            str: 提示语
        """
        return await self.__handle_request(
            bot=bot, id_=id_, type_=type_, approve=False, reason=reason
        )

    def get_group_request(self, id_: int) -> GroupRequest:
        target = self.__data.group_request
        if id_ >= len(target):
            return None
        return target[id_]

    def get_requests(self) -> Requests:
        """获取请求列表

        Returns:
            Requests: rua
        """
        return self.__data
