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

from .data_type import LimitType, CheckType, CountPeriod

_file_path = Path() / "data" / "core" / "count_manager"
_file_path.mkdir(parents=True, exist_ok=True)


class CountItem:
    def __init__(
        self,
        count: int,
        hint: Union[str, Message, None],
        limit_type: LimitType = LimitType.user,
        check_type: CheckType = CheckType.all,
        count_period: CountPeriod = CountPeriod.day,
    ) -> None:
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
    return [0, 0, 0, 0, 0]


class CountManager:
    class PluginCount:
        class CountChecker:
            def __init__(
                self, data: DefaultDict[int, List[int]], count_item: CountItem
            ) -> None:
                limit_type, check_type = count_item.limit_type, count_item.check_type
                self.hint = count_item.hint
                self.__count_limit = count_item.count
                self.__data: DefaultDict[int, List[int]] = (
                    data["user"] if limit_type == LimitType.user else data["group"]
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
                if self.__data[event.user_id][self.__idx] < self.__count_limit:
                    self.__data[event.user_id][self.__idx] += 1
                    return True
                return False

            def __CheckGroup(self, event: Union[MessageEvent, PokeNotifyEvent]) -> bool:
                if type(event) is GroupMessageEvent or type(event) is PokeNotifyEvent:
                    if self.__data[event.group_id][self.__idx] < self.__count_limit:
                        self.__data[event.group_id][self.__idx] += 1
                        return True
                return True

        def __init__(self, plugin_name: str) -> None:
            self.__file = _file_path / plugin_name
            self.__count_data: Dict[str, DefaultDict] = {
                "group": defaultdict(_default),
                "user": defaultdict(_default),
            }
            self.__count_checkers: List[CountManager.PluginCount.CountChecker] = []
            self.__dirty_data: bool = False

        async def Init(self, count_items: Union[CountItem, List[CountItem]]):
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
            for checker in self.__count_checkers:
                if not checker.Check(event):
                    return checker.hint
                self.__dirty_data = True
            return True

        async def Save(self):
            if self.__dirty_data:
                async with aiofiles.open(self.__file, "wb") as f:
                    await f.write(pickle.dumps(self.__count_data))
                self.__dirty_data = False

        def Reset(self, period: CountPeriod):
            p_int = _period_to_int[period]
            for _, counts in self.__count_data["group"].items():
                counts[p_int] = 0
            for _, counts in self.__count_data["user"].items():
                counts[p_int] = 0

    def __init__(self) -> None:
        self.__plugin_count: Dict[str, CountManager.PluginCount] = {}

    async def Add(
        self, plugin_name: str, count_items: Union[List[CountItem], CountItem]
    ) -> None:
        self.__plugin_count[plugin_name] = CountManager.PluginCount(
            plugin_name=plugin_name
        )
        await self.__plugin_count[plugin_name].Init(count_items=count_items)

    def Check(self, plugin_name: str, event: Union[MessageEvent, PokeNotifyEvent]):
        if plugin_count := self.__plugin_count.get(plugin_name):
            if (ret := plugin_count.Check(event=event)) != True:
                return ret
        return True

    async def Save(self) -> None:
        await asyncio.gather(
            *[plugin_count.Save() for plugin_count in self.__plugin_count.values()]
        )

    def Reset(self, period: CountPeriod):
        for plugin_count in self.__plugin_count.values():
            plugin_count.Reset(period)
