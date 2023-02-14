from typing import Dict, Deque, Set
from collections import deque, defaultdict
import time
import asyncio


class GroupCache:
    class CacheItem:
        def __init__(self, url: str, expired_time: int) -> None:
            self.url = url
            self.expired_time = expired_time

    class Group:
        def __init__(self) -> None:
            self.__deque: Deque[GroupCache.CacheItem] = deque()
            self.__set: Set[str] = set()
            asyncio.create_task(self.clean())

        def check(self, url: str) -> bool:
            return url in self.__set

        def add(self, url: str) -> bool:
            self.__deque.appendleft(
                GroupCache.CacheItem(url=url, expired_time=time.time() + 5 * 60)
            )
            self.__set.add(url)

        async def clean(self) -> bool:
            while True:
                now = time.time()
                wait_time = 30
                while len(self.__deque):
                    item = self.__deque.pop()
                    if now >= item.expired_time:
                        self.__set.remove(item.url)
                    else:
                        self.__deque.append(item)
                        wait_time = item.expired_time - now + 0.5
                        break
                await asyncio.sleep(wait_time)

    def __init__(self) -> None:
        self.__data: Dict[int, GroupCache.Group] = defaultdict(
            lambda: GroupCache.Group()
        )

    def check(self, group_id: int, url: str) -> bool:
        """如果URL在里面，返回True

        Args:
            group_id (int): 群号
            url (str): 链接

        Returns:
            bool: 如果URL在里面，返回True
        """
        return self.__data[group_id].check(url)

    def add(self, group_id: int, url: str) -> bool:
        if not self.__data[group_id].check(url):
            self.__data[group_id].add(url)
            return True
        return False


cache = GroupCache()
