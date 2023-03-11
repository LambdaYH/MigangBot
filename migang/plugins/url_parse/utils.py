import time
import asyncio
from collections import deque, defaultdict
from typing import Set, Deque, DefaultDict

from nonebot import get_driver

# 5min
DEFAULT_CACHE_TIME = 30 * 5


class CacheItem:
    def __init__(self, url: str, group_id: int) -> None:
        self.expired: float = time.time() + DEFAULT_CACHE_TIME
        self.cached_url: str = url
        self.group_id: int = group_id


class GroupCache:
    def __init__(self) -> None:
        self.__groups: DefaultDict[int, Set[str]] = defaultdict(lambda: set())
        self.__deque: Deque[CacheItem] = deque()
        self.__event: asyncio.Event = asyncio.Event()

    def init(self) -> None:
        asyncio.create_task(self.__clean_task())

    async def __clean_task(self):
        while True:
            now = time.time()
            if len(self.__deque) != 0 and self.__deque[-1].expired < now:
                item = self.__deque.pop()
                self.__groups[item.group_id].remove(item.cached_url)
            self.__event.clear()
            if len(self.__deque) != 0:
                try:
                    await asyncio.wait_for(
                        self.__event.wait(), timeout=self.__deque[-1].expired - now
                    )
                except asyncio.TimeoutError:
                    pass
            else:
                await self.__event.wait()

    def check(self, group_id: int, url: str) -> bool:
        """如果URL在里面，返回True

        Args:
            group_id (int): 群号
            url (str): 链接

        Returns:
            bool: 如果URL在里面，返回True
        """
        return url in self.__groups[group_id]

    def add(self, group_id: int, url: str) -> bool:
        if url not in self.__groups[group_id]:
            self.__groups[group_id].add(url)
            self.__deque.appendleft(CacheItem(url=url, group_id=group_id))
            self.__event.set()
            return True
        return False


cache = GroupCache()


@get_driver().on_startup
async def _():
    cache.init()
