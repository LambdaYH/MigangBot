from typing import Dict, Union, Callable, List
from time import time

from nonebot.adapters.onebot.v11 import (
    Message,
    MessageEvent,
    GroupMessageEvent,
    PokeNotifyEvent,
)

from .data_class import LimitType, CheckType


class CDItem:
    def __init__(
        self,
        cd: Union[int, float],
        hint: Union[str, Message, None],
        limit_type: LimitType = LimitType.user,
        check_type: CheckType = CheckType.all,
    ) -> None:
        """
        Args:
            cd (Union[int, float]): 插件CD
            hint (Union[str, Message, None]): 当CD未到时的提示语
            limit_type (LimitType, optional): 检查CD的对象，群或用户. Defaults to LimitType.user.
            check_type (CheckType, optional): 检查CD的会话，群聊或私聊或全部. Defaults to CheckType.all.
        """
        self.cd = cd
        self.hint = hint
        self.limit_type = limit_type
        self.check_type = check_type


class CDManager:
    """
    管理插件的cd
    """

    class PluginCD:
        class CDChecker:
            def __init__(self, cd_item: CDItem) -> None:
                self.__cd = cd_item.cd
                self.hint = cd_item.hint
                self.__last_called: Dict[int, float] = {}
                self.__func: Callable = self.__CheckUserPrivate
                limit_type, check_type = cd_item.limit_type, cd_item.check_type
                if limit_type == LimitType.user and check_type == CheckType.private:
                    self.__func = self.__CheckUserPrivate
                elif limit_type == LimitType.user and check_type == CheckType.group:
                    self.__func = self.__CheckUserGroup
                elif limit_type == LimitType.user and check_type == CheckType.all:
                    self.__func = self.__CheckUserAll
                else:
                    self.__func = self.__CheckGroup

            def Check(self, event: Union[MessageEvent, PokeNotifyEvent]) -> bool:
                return self.__func(event)

            def __CheckUserPrivate(
                self, event: Union[MessageEvent, PokeNotifyEvent]
            ) -> bool:
                if type(event) is PokeNotifyEvent or event.message_type[0] == "p":
                    return self.__CheckUserAll(event)
                return True

            def __CheckUserGroup(
                self, event: Union[MessageEvent, PokeNotifyEvent]
            ) -> bool:
                if type(event) is PokeNotifyEvent or event.message_type[0] == "g":
                    return self.__CheckUserAll(event)
                return True

            def __CheckUserAll(
                self, event: Union[MessageEvent, PokeNotifyEvent]
            ) -> bool:
                if (
                    (now := time()) - self.__last_called.get(event.user_id, 0)
                ) > self.__cd:
                    self.__last_called[event.user_id] = now
                    return True
                return False

            def __CheckGroup(self, event: Union[MessageEvent, PokeNotifyEvent]) -> bool:
                if type(event) is GroupMessageEvent or type(event) is PokeNotifyEvent:
                    if (
                        (now := time()) - self.__last_called.get(event.group_id, 0)
                    ) > self.__cd:
                        self.__last_called[event.group_id] = now
                        return True
                    return False
                return True

        def __init__(self, cd_items: Union[List[CDItem], CDItem]):
            if type(cd_items) is list:
                self.__cd_checkers: List[CDManager.PluginCD.CDChecker] = [
                    CDManager.PluginCD.CDChecker(cd_item=cd_item)
                    for cd_item in cd_items
                ]
            else:
                self.__cd_checkers: List[CDManager.PluginCD.CDChecker] = [
                    CDManager.PluginCD.CDChecker(cd_item=cd_items)
                ]

        def Check(
            self, event: Union[MessageEvent, PokeNotifyEvent]
        ) -> Union[str, bool, None]:
            """
            检测CD，当检测通过时返回bool类型，反之其他类型

            Args:
                event (Union[MessageEvent, PokeNotifyEvent]): 事件

            Returns:
                Union[str, bool, None]: 当检测通过时返回bool类型，反之其他类型，代表提示语
            """
            for checker in self.__cd_checkers:
                if not checker.Check(event):
                    return checker.hint
            return True

    def __init__(self) -> None:
        self.__plugin_cd: Dict[str, CDManager.PluginCD] = {}

    def Add(self, plugin_name: str, cd_items: Union[List[CDItem], CDItem]):
        self.__plugin_cd[plugin_name] = CDManager.PluginCD(cd_items=cd_items)

    def Check(
        self, plugin_name: str, event: Union[MessageEvent, PokeNotifyEvent]
    ) -> Union[str, bool, None]:
        if plugin_cd := self.__plugin_cd.get(plugin_name):
            if (ret := plugin_cd.Check(event=event)) != True:
                return ret
        return True
