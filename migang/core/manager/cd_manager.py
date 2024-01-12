from time import time
from typing import Dict, List, Union, Callable, Iterable

from nonebot.adapters import Message

from migang.core.cross_platform import MigangSession

from .data_class import CheckType, LimitType


class CDItem:
    """__plugin_cd__属性为Iterable[CDItem]或CDItem"""

    def __init__(
        self,
        cd: Union[int, float],
        hint: Union[str, Message, None] = None,
        limit_type: LimitType = LimitType.user,
        check_type: CheckType = CheckType.all,
    ) -> None:
        """CDItem构造函数

        Args:
            cd (Union[int, float]): 插件CD
            hint (Union[str, Message, None]): 当还在CD冷却期时，发送的提示语. Defaults to None.
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

            def __init__(
                self, cd_item: CDItem, last_called: Dict[str, Dict[int, float]]
            ) -> None:
                """CDChecker构造函数，根据不同的检测对象与会话类型生成对应的CD检测器

                Args:
                    cd_item (CDItem): cd配置项
                """
                self.__cd = cd_item.cd
                self.hint = cd_item.hint
                self.__last_called: Dict[int, float] = {}
                """该检测器最后的调用时间，{id: time}
                """
                self.__func: Callable[[MigangSession], Union[bool, float]]
                """实际的检测函数
                """
                limit_type, check_type = cd_item.limit_type, cd_item.check_type
                if limit_type is LimitType.user:
                    self.__last_called = last_called["user"]
                    if check_type is CheckType.private:
                        self.__func = self.__check_user_private
                    elif check_type is CheckType.group:
                        self.__func = self.__check_user_group
                    elif check_type is CheckType.all:
                        self.__func = self.__check_user_all
                else:
                    self.__last_called = last_called["group"]
                    self.__func = self.__check_group

            def check(self, session: MigangSession) -> Union[bool, float]:
                """外部可调用的检测函数

                Args:
                    session (MigangSession): 会话

                Returns:
                    Union[bool, float]: 若CD不在冷却期，返回True，反之返回剩余时间
                """
                return self.__func(session)

            def __check_user_private(
                self, session: MigangSession
            ) -> Union[bool, float]:
                """limit_type为user，check_type为private时的具体检测函数

                Args:
                    session (MigangSession): 会话

                Returns:
                    Union[bool, float]: 若CD不在冷却期，返回True，反之返回剩余时间
                """
                if not session.is_group:
                    return self.__check_user_all(session)
                return True

            def __check_user_group(self, session: MigangSession) -> Union[bool, float]:
                """limit_type为user，check_type为group时的具体检测函数

                Args:
                    session (MigangSession): 会话

                Returns:
                    Union[bool, float]: 若CD不在冷却期，返回True，反之返回剩余时间
                """
                if not session.is_group:
                    return self.__check_user_all(session)
                return True

            def __check_user_all(self, session: MigangSession) -> Union[bool, float]:
                """limit_type为user，check_type为all时的具体检测函数

                Args:
                    session (MigangSession): 会话

                Returns:
                    Union[bool, float]: 若CD不在冷却期，返回True，反之返回剩余时间
                """
                if (
                    (now := time()) - self.__last_called.get(session.user_id, 0)
                ) > self.__cd:
                    return True
                else:
                    return self.__cd - (
                        now - self.__last_called.get(session.user_id, 0)
                    )

            def __check_group(self, session: MigangSession) -> Union[bool, float]:
                """limit_type为group，check_type只能是group时的具体检测函数

                Args:
                    session (MigangSession): 会话

                Returns:
                    Union[bool, float]: 若CD不在冷却期，返回True，反之返回剩余时间
                """
                if session.is_group:
                    if (
                        (now := time()) - self.__last_called.get(session.group_id, 0)
                    ) > self.__cd:
                        return True
                    else:
                        return self.__cd - (
                            now - self.__last_called.get(session.group_id, 0)
                        )
                return True

        def __init__(self, cd_items: Union[Iterable[CDItem], CDItem]) -> None:
            """PluginCD的构造函数，获取插件中的所有CD控制项，创建对应的CDChecker并接手该插件CD的管理

            Args:
                cd_items (Union[Iterable[CDItem], CDItem]): 该插件中的CD控制项
            """
            self.__last_called: Dict[str, Dict[int, float]] = {"group": {}, "user": {}}
            """插件最后调用时间{"group": {}, "user": {}}
            """
            self.__cd_checkers: List[CDManager.PluginCD.CDChecker]
            """保存该插件中的各CD检测器
            """
            if isinstance(cd_items, CDItem):
                cd_items = (cd_items,)
            self.__cd_checkers: List[CDManager.PluginCD.CDChecker] = [
                CDManager.PluginCD.CDChecker(
                    cd_item=cd_item, last_called=self.__last_called
                )
                for cd_item in cd_items
            ]

        def check(self, session: MigangSession) -> Union[str, bool, None]:
            """
            检测CD，若CD不在冷却期，返回True，反之返回提示语

            Args:
                session (MigangSession): 会话

            Returns:
                Union[str, bool, None]: 若CD不在冷却期，返回True，反之返回提示语
            """
            for checker in self.__cd_checkers:
                if (ret := checker.check(session)) != True:
                    if checker.hint != None:
                        if isinstance(checker.hint, Message):
                            return Message(
                                str(checker.hint).replace(
                                    "&#91;_剩余时间_&#93;", f"{ret:.2f}"
                                )
                            )
                        return checker.hint.replace("[_剩余时间_]", f"{ret:.2f}")
                    return None
            # 更新调用时间，和检测时候可能会有一点点的时间差
            now = time()
            if session.is_group:
                self.__last_called["group"][session.group_id] = now
            self.__last_called["user"][session.user_id] = now
            return True

    def __init__(self) -> None:
        """CDManager构造函数，由于CD配置不固化到硬盘，因此每次程序启动时都重新加载"""
        self.__plugin_cd: Dict[str, CDManager.PluginCD] = {}
        """{plugin_name: PluginCD}，以plugin_name为名的插件调用PluginCD检测调用次数
        """

    def add(
        self, plugin_name: str, cd_items: Union[Iterable[CDItem], CDItem, int, float]
    ):
        """添加插件以及其对应的__plugin_cd__配置项（若有）进CDManager

        Args:
            plugin_name (str): 插件名（plugin.name）
            cd_items (Union[Iterable[CDItem], CDItem, int, float]): __plugin_cd__内容
        """
        if isinstance(cd_items, int) or isinstance(cd_items, float):
            cd_items = CDItem(cd_items)
        self.__plugin_cd[plugin_name] = CDManager.PluginCD(cd_items=cd_items)

    def check(self, plugin_name: str, session: MigangSession) -> Union[str, bool, None]:
        """检测plugin_name 的 CD，若CD不在冷却期，返回True，反之返回提示语

        Args:
            plugin_name (str): 插件名（plugin.name）
            session (MigangSession): 会话

        Returns:
            Union[str, bool, None]: 若CD不在冷却期，返回True，反之返回提示语
        """
        if plugin_cd := self.__plugin_cd.get(plugin_name):
            if (ret := plugin_cd.check(session)) != True:
                return ret
        return True
