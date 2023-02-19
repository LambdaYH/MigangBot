import anyio
import asyncio
from pathlib import Path
from pydantic import BaseModel
from typing import List, Union, Dict, Callable, Iterable

from nonebot.adapters.onebot.v11 import (
    Message,
    Event,
)

from .data_class import LimitType, CheckType, CountPeriod


class CountItem:
    """__plugin_count__属性为Iterable[CountItem]或CountItem"""

    def __init__(
        self,
        count: int,
        hint: Union[str, Message, None] = None,
        limit_type: LimitType = LimitType.user,
        check_type: CheckType = CheckType.all,
        count_period: CountPeriod = CountPeriod.day,
    ) -> None:
        """CountItem构造函数

        Args:
            count (int): 插件调用次数限制
            hint (Union[str, Message, None]): 当插件达到调用次数上限后，发送的提示语. Defaults to None.
            limit_type (LimitType, optional): 限制检测的对象为用户或群. Defaults to LimitType.user.
            check_type (CheckType, optional): 限制检测的会话为私聊或群聊或全部. Defaults to CheckType.all.
            count_period (CountPeriod, optional): 计数周期. Defaults to CountPeriod.day.
        """
        self.count = count
        self.hint = hint
        self.limit_type = limit_type
        self.check_type = check_type
        self.count_period = count_period


class Counter(BaseModel):
    """存储单个插件计数数据的数据结构"""

    user: Dict[int, List[int]] = {}
    group: Dict[int, List[int]] = {}


class CountManager:
    """管理插件调用计数"""

    class PluginCount:
        """管理单个插件调用计数"""

        class CountChecker:
            """根据不同的检测对象与会话类型生成对应的调用计数检测器"""

            def __init__(self, data: Counter, count_item: CountItem) -> None:
                """CountChecker构造函数，根据不同的检测对象与会话类型生成对应的调用计数检测器

                Args:
                    data (Counter): 插件所属的数据
                    count_item (CountItem): 调用次数配置项
                """
                limit_type, check_type = count_item.limit_type, count_item.check_type
                self.hint = count_item.hint
                self.__count_limit = count_item.count
                self.__data: Dict[int, List[int]] = (
                    data.user if limit_type == LimitType.user else data.group
                )
                self.__idx: int = count_item.count_period._value_
                self.__func: Callable[[Event]]
                self.__update_func: Callable[[Event]]
                if limit_type is LimitType.user:
                    self.__update_func = self.__update_user
                    if check_type is CheckType.private:
                        self.__func = self.__check_user_private
                    elif check_type is CheckType.group:
                        self.__func = self.__check_user_group
                    elif check_type is CheckType.all:
                        self.__func = self.__check_user_all
                else:
                    self.__update_func = self.__update_group
                    self.__func = self.__check_group

            def check(self, event: Event) -> bool:
                """外部可调用的检测函数

                Args:
                    event (Event): 事件

                Returns:
                    bool: 若未达到调用上限，返回True
                """
                return self.__func(event)

            def update(self, event: Event):
                """更新计数

                Args:
                    event (Event): 事件
                """
                self.__update_func(event)

            def __get_user(self, user_id: int) -> List[int]:
                user = self.__data.get(user_id)
                if user is None:
                    user = self.__data[user_id] = [0] * 5
                return user

            def __get_group(self, group_id: int) -> List[int]:
                group = self.__data.get(group_id)
                if group is None:
                    group = self.__data[group_id] = [0] * 5
                return group

            def __update_user(self, event: Event) -> None:
                """更新用户计数

                Args:
                    event (Event): 事件
                """
                if hasattr(event, "user_id"):
                    self.__get_user(user_id=event.user_id)[self.__idx] += 1

            def __update_group(self, event: Event) -> None:
                """更新群计数

                Args:
                    event (Event): 事件
                """
                if hasattr(event, "group_id"):
                    self.__get_group(group_id=event.group_id)[self.__idx] += 1

            def __check_user_private(self, event: Event) -> bool:
                """limit_type为user，check_type为private时的具体检测函数

                Args:
                    event (Event): 事件

                Returns:
                    bool: 若未达到调用上限，返回True
                """
                if not hasattr(event, "group_id"):
                    return self.__check_user_all(event)
                return True

            def __check_user_group(self, event: Event) -> bool:
                """limit_type为user，check_type为group时的具体检测函数

                Args:
                    event (Event): 事件

                Returns:
                    bool: 若未达到调用上限，返回True
                """
                if hasattr(event, "group_id"):
                    return self.__check_user_all(event)
                return True

            def __check_user_all(self, event: Event) -> bool:
                """limit_type为user，check_type为all时的具体检测函数

                Args:
                    event (Event): 事件

                Returns:
                    bool: 若未达到调用上限，返回True
                """
                if hasattr(event, "user_id"):
                    if (
                        self.__get_user(user_id=event.user_id)[self.__idx]
                        < self.__count_limit
                    ):
                        return True
                    return False
                return True

            def __check_group(self, event: Event) -> bool:
                """limit_type为user，check_type只能是group时的具体检测函数数

                Args:
                    event (Event): 事件

                Returns:
                    bool: 若未达到调用上限，返回True
                """
                if hasattr(event, "group_id"):
                    if (
                        self.__get_group(group_id=event.group_id)[self.__idx]
                        < self.__count_limit
                    ):
                        return True
                return True

        def __init__(self, file: Path) -> None:
            """PluginCount构造函数，管理单插件的调用计数

            Args:
                plugin_name (str): 插件名
            """
            self.__file = file
            self.__count_data: Counter
            self.__count_checkers: List[CountManager.PluginCount.CountChecker] = []
            self.__dirty_data: bool = False

        async def init(self, count_items: Union[CountItem, Iterable[CountItem]]):
            """异步初始化，从文件中读取调用计数记录并加载到内存，同时载入调用次数配置

            Args:
                count_items (Union[CountItem, Iterable[CountItem]]): 调用次数配置项
            """
            if self.__file.exists():
                async with await anyio.open_file(self.__file, "r") as f:
                    self.__count_data = Counter.parse_raw(await f.read())
            else:
                self.__count_data = Counter()
            if isinstance(count_items, Iterable):
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

        def check(self, event: Event) -> Union[str, bool, None]:
            """检测插件对应的调用次数，若未达到上限，返回True，反之返回提示语

            Args:
                event (Event): 事件

            Returns:
                Union[str, bool, None]: 若未达到调用次数上限，返回True，反之返回提示语
            """
            for checker in self.__count_checkers:
                if not checker.check(event):
                    return checker.hint
            # 更新计数
            for checker in self.__count_checkers:
                checker.update(event)
            self.__dirty_data = True
            return True

        async def save(self) -> None:
            """将调用次数保存在硬盘"""
            if self.__dirty_data:
                async with await anyio.open_file(self.__file, "w") as f:
                    await f.write(self.__count_data.json(indent=4))
                self.__dirty_data = False

        def reset(self, period: CountPeriod) -> None:
            """重置调用次数

            Args:
                period (CountPeriod): 所需重置的对应周期
            """
            for counts in self.__count_data.group.values():
                counts[period._value_] = 0
            for counts in self.__count_data.user.values():
                counts[period._value_] = 0
            self.__dirty_data = True

    def __init__(self, path: Path) -> None:
        """CountManager构造函数"""
        self.__plugin_count: Dict[str, CountManager.PluginCount] = {}
        self.__path: Path = path
        self.__path.mkdir(exist_ok=True, parents=True)

    async def add(
        self, plugin_name: str, count_items: Union[Iterable[CountItem], CountItem, int]
    ) -> None:
        """添加plugin_name对应的插件中的调用次数限制配置，由CountManager接手调用次数限制

        Args:
            plugin_name (str): 插件名
            count_items (Union[Iterable[CountItem], CountItem, int]): 插件计数配置们
        """
        self.__plugin_count[plugin_name] = CountManager.PluginCount(
            file=self.__path / f"{plugin_name}.json"
        )
        if isinstance(count_items, int):
            count_items = CountItem(count_items)
        await self.__plugin_count[plugin_name].init(count_items=count_items)

    def check(self, plugin_name: str, event: Event) -> Union[str, bool, None]:
        """检测插件plugin_name对应的调用次数，若未达到上限，返回True，反之返回提示语

        Args:
            plugin_name (str): 插件名
            event (Event): 事件

        Returns:
            Union[str, bool, None]: 若未达到调用次数上限，返回True，反之返回提示语
        """
        if plugin_count := self.__plugin_count.get(plugin_name):
            if (ret := plugin_count.check(event=event)) != True:
                return ret
        return True

    async def save(self) -> None:
        """保存所有插件的调用次数记录进硬盘"""
        await asyncio.gather(
            *[plugin_count.save() for plugin_count in self.__plugin_count.values()]
        )

    def reset(self, period: CountPeriod) -> None:
        """重置调用次数

        Args:
            period (CountPeriod): 所需重置的对应周期
        """
        for plugin_count in self.__plugin_count.values():
            plugin_count.reset(period)
        
