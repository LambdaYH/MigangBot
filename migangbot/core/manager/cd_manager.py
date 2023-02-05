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
    """__plugin_cd__属性为List[CDItem]或CDItem"""

    def __init__(
        self,
        cd: Union[int, float],
        hint: Union[str, Message, None],
        limit_type: LimitType = LimitType.user,
        check_type: CheckType = CheckType.all,
    ) -> None:
        """CDItem构造函数

        Args:
            cd (Union[int, float]): 插件CD
            hint (Union[str, Message, None]): 当还在CD冷却期时，发送的提示语
            limit_type (LimitType, optional): 限制检测CD的对象为用户或群. Defaults to LimitType.user.
            check_type (CheckType, optional): 限制检测CD的会话为私聊或群聊或全部. Defaults to CheckType.all.
        """

        self.cd = cd
        self.hint = hint
        self.limit_type = limit_type
        self.check_type = check_type


class CDManager:
    """
    管理插件的CD
    """

    class PluginCD:
        """管理单个插件的CD"""

        class CDChecker:
            """根据不同的检测对象与会话类型生成对应的CD检测器"""

            def __init__(self, cd_item: CDItem) -> None:
                """CDChecker构造函数，根据不同的检测对象与会话类型生成对应的CD检测器

                Args:
                    cd_item (CDItem): cd配置项
                """
                self.__cd = cd_item.cd
                self.hint = cd_item.hint
                self.__last_called: Dict[int, float] = {}
                """该检测器最后的调用时间，{id: time}
                """
                self.__func: Callable = self.__check_user_private
                """实际的检测函数
                """
                limit_type, check_type = cd_item.limit_type, cd_item.check_type
                if limit_type == LimitType.user and check_type == CheckType.private:
                    self.__func = self.__check_user_private
                elif limit_type == LimitType.user and check_type == CheckType.group:
                    self.__func = self.__check_user_group
                elif limit_type == LimitType.user and check_type == CheckType.all:
                    self.__func = self.__check_user_all
                else:
                    self.__func = self.__check_group

            def check(self, event: Union[MessageEvent, PokeNotifyEvent]) -> bool:
                """外部可调用的检测函数

                Args:
                    event (Union[MessageEvent, PokeNotifyEvent]): 事件

                Returns:
                    bool: 若CD不在冷却期，返回True
                """
                return self.__func(event)

            def __check_user_private(
                self, event: Union[MessageEvent, PokeNotifyEvent]
            ) -> bool:
                """limit_type为user，check_type为private时的具体检测函数

                Args:
                    event (Union[MessageEvent, PokeNotifyEvent]): 事件

                Returns:
                    bool: 若CD不在冷却期，返回True
                """
                if type(event) is PokeNotifyEvent or event.message_type[0] == "p":
                    return self.__check_user_all(event)
                return True

            def __check_user_group(
                self, event: Union[MessageEvent, PokeNotifyEvent]
            ) -> bool:
                """limit_type为user，check_type为group时的具体检测函数

                Args:
                    event (Union[MessageEvent, PokeNotifyEvent]): 事件

                Returns:
                    bool: 若CD不在冷却期，返回True
                """
                if type(event) is PokeNotifyEvent or event.message_type[0] == "g":
                    return self.__check_user_all(event)
                return True

            def __check_user_all(
                self, event: Union[MessageEvent, PokeNotifyEvent]
            ) -> bool:
                """limit_type为user，check_type为all时的具体检测函数

                Args:
                    event (Union[MessageEvent, PokeNotifyEvent]): 事件

                Returns:
                    bool: 若CD不在冷却期，返回True
                """
                if (
                    (now := time()) - self.__last_called.get(event.user_id, 0)
                ) > self.__cd:
                    self.__last_called[event.user_id] = now
                    return True
                return False

            def __check_group(self, event: Union[MessageEvent, PokeNotifyEvent]) -> bool:
                """limit_type为group，check_type只能是group时的具体检测函数

                Args:
                    event (Union[MessageEvent, PokeNotifyEvent]): 事件

                Returns:
                    bool: 若CD不在冷却期，返回True
                """
                if type(event) is GroupMessageEvent or type(event) is PokeNotifyEvent:
                    if (
                        (now := time()) - self.__last_called.get(event.group_id, 0)
                    ) > self.__cd:
                        self.__last_called[event.group_id] = now
                        return True
                    return False
                return True

        def __init__(self, cd_items: Union[List[CDItem], CDItem]) -> None:
            """PluginCD的构造函数，获取插件中的所有CD控制项，创建对应的CDChecker并接手该插件CD的管理

            Args:
                cd_items (Union[List[CDItem], CDItem]): 该插件中的CD控制项
            """
            self.__cd_checkers: List[CDManager.PluginCD.CDChecker]
            """保存该插件中的各CD检测器
            """
            if type(cd_items) is list:
                self.__cd_checkers: List[CDManager.PluginCD.CDChecker] = [
                    CDManager.PluginCD.CDChecker(cd_item=cd_item)
                    for cd_item in cd_items
                ]
            else:
                self.__cd_checkers: List[CDManager.PluginCD.CDChecker] = [
                    CDManager.PluginCD.CDChecker(cd_item=cd_items)
                ]

        def check(
            self, event: Union[MessageEvent, PokeNotifyEvent]
        ) -> Union[str, bool, None]:
            """
            检测CD，若CD不在冷却期，返回True，反之返回提示语

            Args:
                event (Union[MessageEvent, PokeNotifyEvent]): 事件

            Returns:
                Union[str, bool, None]: 若CD不在冷却期，返回True，反之返回提示语
            """
            for checker in self.__cd_checkers:
                if not checker.check(event):
                    return checker.hint
            return True

    def __init__(self) -> None:
        """CDManager构造函数，由于CD配置不固化到硬盘，因此每次程序启动时都重新加载"""
        self.__plugin_cd: Dict[str, CDManager.PluginCD] = {}
        """{plugin_name: PluginCD}，以plugin_name为名的插件调用PluginCD检测调用次数
        """

    def add(self, plugin_name: str, cd_items: Union[List[CDItem], CDItem]):
        """添加插件以及其对应的__plugin_cd__配置项（若有）进CDManager

        Args:
            plugin_name (str): 插件名（plugin.name）
            cd_items (Union[List[CDItem], CDItem]): __plugin_cd__内容
        """
        self.__plugin_cd[plugin_name] = CDManager.PluginCD(cd_items=cd_items)

    def check(
        self, plugin_name: str, event: Union[MessageEvent, PokeNotifyEvent]
    ) -> Union[str, bool, None]:
        """检测plugin_name 的 CD，若CD不在冷却期，返回True，反之返回提示语

        Args:
            plugin_name (str): 插件名（plugin.name）
            event (Union[MessageEvent, PokeNotifyEvent]): 事件

        Returns:
            Union[str, bool, None]: 若CD不在冷却期，返回True，反之返回提示语
        """
        if plugin_cd := self.__plugin_cd.get(plugin_name):
            if (ret := plugin_cd.check(event=event)) != True:
                return ret
        return True
