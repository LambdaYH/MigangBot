import time
import random
import inspect
from asyncio import iscoroutinefunction
from typing import Any, Dict, List, Tuple, Union, Callable, Coroutine

from nonebot.matcher import Matcher
from nonebot_plugin_alconna import UniMessage
from nonebot.adapters import Bot, Event, Message

from migang.core.permission import BLACK
from migang.core.manager import permission_manager
from migang.core.cross_platform import MigangSession

from .exception import BreakSession


class MessageManager:
    def __init__(
        self,
        *get_reply_func: Callable[
            [UniMessage, int],
            Union[
                Coroutine[Any, Any, str],
                str,
                UniMessage,
                Coroutine[Any, Any, UniMessage],
            ],
        ],
    ) -> None:
        self.__same_ret = [
            "为什么要发一样的话？",
            "请不要再重复对我说一句话了，不然我就要生气了！",
            "别再发这句话了，我已经知道了...",
            "救命！有笨蛋一直给{nickname}发一样的话！",
            "这句话你已经给我发了{count}次了，再发就生气！",
        ]
        self.__repeat_ret = [
            "请不要学{nickname}说话",
            "为什么要一直学{nickname}说话？",
            "你再学！你再学我就生气了！",
            "呜呜，你是想欺负{nickname}嘛..",
            "{user_name}不要再学我说话了！",
            "再学我说话，我就把你拉进黑名单（生气",
            "别再学了！",
        ]
        self.__data: Dict[int, Dict[str, Union[float, int, List[str]]]] = {}
        self.__get_reply: Tuple[
            Callable[
                [UniMessage, int],
                Union[
                    Coroutine[Any, Any, str], str, Message, Coroutine[Any, Any, Message]
                ],
            ]
        ] = get_reply_func

    async def reply(
        self,
        session: MigangSession,
        user_name: str,
        nickname: str,
        bot: Bot,
        plain_text: str,
        matcher: Matcher,
        event: Event,
        message: UniMessage,
    ) -> UniMessage:
        msg_str = event.get_plaintext()
        if count := self.__check_repeat(user_id=session.user_id, msg=msg_str):
            if count >= 3:
                permission_manager.set_user_perm(
                    user_id=session.user_id, permission=BLACK, duration=5 * 60
                )
                return "生气了！不和你说话了（5min）"
            return UniMessage.text(
                random.choice(self.__same_ret).format(
                    nickname=nickname, count=count + 1
                )
            )
        if self.__check_follow_me(user_id=session.user_id, msg=msg_str):
            return UniMessage.text(
                random.choice(self.__repeat_ret).format(
                    nickname=nickname, user_name=user_name
                )
            )
        for func in self.__get_reply:
            args = inspect.signature(func).parameters.keys()
            params = {}
            if "user_id" in args:
                params["user_id"] = session.user_id
            if "user_name" in args:
                params["user_name"] = user_name
            if "bot" in args:
                params["bot"] = bot
            if "plain_text" in args:
                params["plain_text"] = plain_text
            if "event" in args:
                params["event"] = event
            if "nickname" in args:
                params["nickname"] = nickname
            if "matcher" in args:
                params["matcher"] = matcher
            if "message" in args:
                params["message"] = message
            if "session" in args:
                params["session"] = session
            try:
                if (
                    reply_ := await func(**params)
                    if iscoroutinefunction(func)
                    else func(**params)
                ):
                    self.__add(user_id=session.user_id, msg=msg_str, reply=reply_)
                    if isinstance(reply_, str):
                        return UniMessage.text(reply_)
                    elif isinstance(reply_, UniMessage):
                        return reply_
            except BreakSession:
                return None
        return UniMessage.text("......(不知道说什么)")

    def __get_user(self, user_id: str) -> Dict:
        user = self.__data.get(user_id)
        if not user:
            user = self.__data[user_id] = {
                "last_message": None,
                "last_reply": None,
                "time": 0,
                "repeat_count": 0,
            }
        return user

    def __add(self, user_id: str, msg: str, reply: str):
        user = self.__get_user(user_id=user_id)
        user["last_message"] = msg
        user["last_reply"] = reply
        user["time"] = time.time()
        user["repeat_count"] = 0

    def __check_repeat(self, user_id: str, msg: str) -> int:
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

    def __check_follow_me(self, user_id: str, msg: str) -> bool:
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
