import pickle
import aiofiles
import asyncio
from pathlib import Path
from collections import defaultdict
from typing import List, Union, Dict, Callable, DefaultDict

from nonebot.adapters.onebot.v11 import (
    Message,
    MessageEvent,
    GroupMessageEvent,
    PokeNotifyEvent,
)

from .data_class import LimitType, CheckType, CountPeriod

_file_path = Path() / "data" / "core" / "count_manager"
_file_path.mkdir(parents=True, exist_ok=True)


class CountItem:
    """__plugin_count__属性为List[CountItem]或CountItem"""

    def __init__(
        self,
        count: int,
        hint: Union[str, Message, None],
        limit_type: LimitType = LimitType.user,
        check_type: CheckType = CheckType.all,
        count_period: CountPeriod = CountPeriod.day,
    ) -> None:
        """CountItem构造函数

        Args:
            count (int): 插件调用次数限制
            hint (Union[str, Message, None]): 当插件达到调用次数上限后，发送的提示语
            limit_type (LimitType, optional): 限制检测的对象为用户或群. Defaults to LimitType.user.
            check_type (CheckType, optional): 限制检测的会话为私聊或群聊或全部. Defaults to CheckType.all.
            count_period (CountPeriod, optional): 计数周期. Defaults to CountPeriod.day.
        """
        self.count = count
        self.hint = hint
        self.limit_type = limit_type
        self.check_type = check_type
        self.count_period = count_period


_period_to_int = {
    CountPeriod.day: 0,
    CountPeriod.hour: 1,
    CountPeriod.week: 2,
    CountPeriod.month: 3,
    CountPeriod.year: 4,
}


def _default():
    return [0] * 5


class CountManager:
    """管理插件调用计数"""

    class PluginCount:
        """管理单个插件调用计数"""

        class Counter:
            """存储单个插件计数数据的数据结构"""

            def __init__(self) -> None:
                self.user: DefaultDict[int, List[int]] = defaultdict(_default)
                self.group: DefaultDict[int, List[int]] = defaultdict(_default)

        class CountChecker:
            """根据不同的检测对象与会话类型生成对应的调用计数检测器"""

            def __init__(self, data, count_item: CountItem) -> None:
                """CountChecker构造函数，根据不同的检测对象与会话类型生成对应的调用计数检测器

                Args:
                    data (CountManager.PluginCount.Counter): 插件所属的数据
                    count_item (CountItem): 调用次数配置项
                """
                limit_type, check_type = count_item.limit_type, count_item.check_type
                self.hint = count_item.hint
                self.__count_limit = count_item.count
                self.__data: DefaultDict[int, List[int]] = (
                    data.user if limit_type == LimitType.user else data.group
                )
                self.__idx: int = _period_to_int[count_item.count_period]
                self.__func: Callable = self.__CheckUserPrivate
                if limit_type == LimitType.user and check_type == CheckType.private:
                    self.__func = self.__CheckUserPrivate
                elif limit_type == LimitType.user and check_type == CheckType.group:
                    self.__func = self.__CheckUserGroup
                elif limit_type == LimitType.user and check_type == CheckType.all:
                    self.__func = self.__CheckUserAll
                else:
                    self.__func = self.__CheckGroup

            def Check(self, event) -> bool:
                """外部可调用的检测函数

                Args:
                    event (Union[MessageEvent, PokeNotifyEvent]): 事件

                Returns:
                    bool: 若未达到调用上限，返回True
                """
                return self.__func(event)

            def __CheckUserPrivate(
                self, event: Union[MessageEvent, PokeNotifyEvent]
            ) -> bool:
                """limit_type为user，check_type为private时的具体检测函数

                Args:
                    event (Union[MessageEvent, PokeNotifyEvent]): 事件

                Returns:
                    bool: 若未达到调用上限，返回True
                """
                if type(event) is PokeNotifyEvent or event.message_type[0] == "p":
                    return self.__CheckUserAll(event)
                return True

            def __CheckUserGroup(
                self, event: Union[MessageEvent, PokeNotifyEvent]
            ) -> bool:
                """limit_type为user，check_type为group时的具体检测函数

                Args:
                    event (Union[MessageEvent, PokeNotifyEvent]): 事件

                Returns:
                    bool: 若未达到调用上限，返回True
                """
                if type(event) is PokeNotifyEvent or event.message_type[0] == "g":
                    return self.__CheckUserAll(event)
                return True

            def __CheckUserAll(
                self, event: Union[MessageEvent, PokeNotifyEvent]
            ) -> bool:
                """limit_type为user，check_type为all时的具体检测函数

                Args:
                    event (Union[MessageEvent, PokeNotifyEvent]): 事件

                Returns:
                    bool: 若未达到调用上限，返回True
                """
                if self.__data[event.user_id][self.__idx] < self.__count_limit:
                    self.__data[event.user_id][self.__idx] += 1
                    return True
                return False

            def __CheckGroup(self, event: Union[MessageEvent, PokeNotifyEvent]) -> bool:
                """limit_type为user，check_type只能是group时的具体检测函数数

                Args:
                    event (Union[MessageEvent, PokeNotifyEvent]): 事件

                Returns:
                    bool: 若未达到调用上限，返回True
                """
                if type(event) is GroupMessageEvent or type(event) is PokeNotifyEvent:
                    if self.__data[event.group_id][self.__idx] < self.__count_limit:
                        self.__data[event.group_id][self.__idx] += 1
                        return True
                return True

        def __init__(self, plugin_name: str) -> None:
            """PluginCount构造函数，管理单插件的调用计数

            Args:
                plugin_name (str): 插件名
            """
            self.__file = _file_path / plugin_name
            self.__count_data: CountManager.PluginCount.Counter = (
                CountManager.PluginCount.Counter()
            )
            self.__count_checkers: List[CountManager.PluginCount.CountChecker] = []
            self.__dirty_data: bool = False

        async def Init(self, count_items: Union[CountItem, List[CountItem]]):
            """异步初始化，从文件中读取调用计数记录并加载到内存，同时载入调用次数配置

            Args:
                count_items (Union[CountItem, List[CountItem]]): 调用次数配置项
            """
            if self.__file.exists():
                async with aiofiles.open(self.__file, "rb") as f:
                    data = await f.read()
                    self.__count_data = pickle.loads(data)
            if type(count_items) is list:
                unique_period = set()
                for count_item in count_items:
                    if count_item.count_period in unique_period:
                        continue
                    self.__count_checkers.append(
                        CountManager.PluginCount.CountChecker(
                            self.__count_data, count_item=count_item
                        )
                    )

            else:
                self.__count_checkers.append(
                    CountManager.PluginCount.CountChecker(
                        self.__count_data, count_item=count_items
                    )
                )

        def Check(self, event) -> Union[str, bool, None]:
            """检测插件对应的调用次数，若未达到上限，返回True，反之返回提示语

            Args:
                event (_type_): 事件

            Returns:
                Union[str, bool, None]: 若未达到调用次数上限，返回True，反之返回提示语
            """
            for checker in self.__count_checkers:
                if not checker.Check(event):
                    return checker.hint
                self.__dirty_data = True
            return True

        async def Save(self) -> None:
            """将调用次数保存在硬盘"""
            if self.__dirty_data:
                async with aiofiles.open(self.__file, "wb") as f:
                    await f.write(pickle.dumps(self.__count_data))
                self.__dirty_data = False

        def Reset(self, period: CountPeriod) -> None:
            """重置调用次数

            Args:
                period (CountPeriod): 所需重置的对应周期
            """
            p_int = _period_to_int[period]
            for counts in self.__count_data.group.values():
                counts[p_int] = 0
            for counts in self.__count_data.user.values():
                counts[p_int] = 0
            self.__dirty_data = True

    def __init__(self) -> None:
        """CountManager构造函数"""
        self.__plugin_count: Dict[str, CountManager.PluginCount] = {}

    async def Add(
        self, plugin_name: str, count_items: Union[List[CountItem], CountItem]
    ) -> None:
        """添加plugin_name对应的插件中的调用次数限制配置，由CountManager接手调用次数限制

        Args:
            plugin_name (str): _description_
            count_items (Union[List[CountItem], CountItem]): _description_
        """
        self.__plugin_count[plugin_name] = CountManager.PluginCount(
            plugin_name=plugin_name
        )
        await self.__plugin_count[plugin_name].Init(count_items=count_items)

    def Check(
        self, plugin_name: str, event: Union[MessageEvent, PokeNotifyEvent]
    ) -> Union[str, bool, None]:
        """检测插件plugin_name对应的调用次数，若未达到上限，返回True，反之返回提示语

        Args:
            plugin_name (str): 插件名
            event (Union[MessageEvent, PokeNotifyEvent]): 事件

        Returns:
            Union[str, bool, None]: 若未达到调用次数上限，返回True，反之返回提示语
        """
        if plugin_count := self.__plugin_count.get(plugin_name):
            if (ret := plugin_count.Check(event=event)) != True:
                return ret
        return True

    async def Save(self) -> None:
        """保存所有插件的调用次数记录进硬盘"""
        await asyncio.gather(
            *[plugin_count.Save() for plugin_count in self.__plugin_count.values()]
        )

    def Reset(self, period: CountPeriod) -> None:
        """重置调用次数

        Args:
            period (CountPeriod): 所需重置的对应周期
        """
        for plugin_count in self.__plugin_count.values():
            plugin_count.Reset(period)
