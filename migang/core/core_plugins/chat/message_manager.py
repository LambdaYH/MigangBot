import random
import time
from asyncio import iscoroutinefunction
from typing import Any, Callable, Coroutine, Dict, List, Tuple, Union

from nonebot.adapters.onebot.v11 import Message


class MessageManager:
    def __init__(
        self,
        *get_reply_func: Callable[
            [Message, int],
            Union[Coroutine[Any, Any, str], str, Message, Coroutine[Any, Any, Message]],
        ],
    ) -> None:
        self.__same_ret = [
            "为什么要发一样的话？",
            "请不要再重复对我说一句话了，不然我就要生气了！",
            "别再发这句话了，我已经知道了...",
            "救命！有笨蛋一直给{nickname}发一样的话！",
            "这句话你已经给我发了[_count_]次了，再发就生气！",
        ]
        self.__repeat_ret = [
            "请不要学{nickname}说话",
            "为什么要一直学{nickname}说话？",
            "你再学！你再学我就生气了！",
            "呜呜，你是想欺负{nickname}嘛..",
            "[_user_name_]不要再学我说话了！",
            "再学我说话，我就把你拉进黑名单（生气",
            "别再学了！",
        ]
        self.__data: Dict[int, Dict[str, Union[float, int, List[str]]]] = {}
        self.__get_reply: Tuple[
            Callable[
                [Message, int],
                Union[
                    Coroutine[Any, Any, str], str, Message, Coroutine[Any, Any, Message]
                ],
            ]
        ] = get_reply_func

    async def reply(
        self, user_id: int, nickname: str, user_name: str, msg: Message
    ) -> Message:
        msg_str = str(msg)
        if count := self.__check_repeat(user_id=user_id, msg=msg_str):
            return (
                random.choice(self.__same_ret)
                .replace("[_count_]", str(count + 1))
                .format(nickname=nickname)
            )
        if self.__check_follow_me(user_id=user_id, msg=msg_str):
            return (
                random.choice(self.__repeat_ret)
                .replace("[_user_name_]", user_name)
                .format(nickname=nickname)
            )
        for func in self.__get_reply:
            if (
                reply_ := await func(msg, user_id)
                if iscoroutinefunction(func)
                else func(msg, user_id)
            ):
                self.__add(user_id=user_id, msg=msg_str, reply=reply_)
                return Message(str(reply_).format(nickname=nickname))
        return "......(不知道说什么)"

    def __get_user(self, user_id: int) -> Dict:
        user = self.__data.get(user_id)
        if not user:
            user = self.__data[user_id] = {
                "last_message": None,
                "last_reply": None,
                "time": 0,
                "repeat_count": 0,
            }
        return user

    def __add(self, user_id: int, msg: str, reply: str):
        user = self.__get_user(user_id=user_id)
        user["last_message"] = msg
        user["last_reply"] = reply
        user["time"] = time.time()
        user["repeat_count"] = 0

    def __check_repeat(self, user_id: int, msg: str) -> int:
        """检查是否重复问问题，若是，返回重复次数（超过5min就不算重复了）

        Args:
            user_id (int): 用户id
            msg (str): 消息

        Returns:
            int: 若重复返回重复次数，反之返回0
        """
        user = self.__get_user(user_id=user_id)
        if msg == user["last_message"]:
            if time.time() - user["time"] >= 5 * 60:
                user["repeat_count"] = 0
            else:
                user["repeat_count"] += 1
        else:
            return 0
        return user["repeat_count"]

    def __check_follow_me(self, user_id: int, msg: str) -> bool:
        """检查是否学我说话，不管怎样就是不能学

        Args:
            user_id (int): 用户id
            msg (str): 消息

        Returns:
            bool: 若学我说话，则返回True
        """
        user = self.__get_user(user_id=user_id)
        if msg == user["last_reply"]:
            return True
        return False
