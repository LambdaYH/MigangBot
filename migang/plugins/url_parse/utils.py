import asyncio
from functools import partial
from collections import defaultdict
from typing import Any, Set, Dict, List, Tuple, Callable, Optional, DefaultDict

import aiohttp
from aiocache import cached
from nonebot.log import logger
from pygtrie import StringTrie
from nonebot.adapters.onebot.v11 import Message

from migang.core import check_task

# 5min
DEFAULT_CACHE_TIME = 30 * 5

ALIAS_DOMAIN = (
    "https://b23.tv",
    "https://m.bilibili.com",
    "https://bilibili.com",
)


@cached(ttl=300)
async def get_url(url):
    async with aiohttp.ClientSession() as client:
        r = await client.head(url, timeout=15, allow_redirects=False)
        if 300 <= r.status <= 399:
            return r.headers["location"]
    return url


class GroupCache:
    def __init__(self) -> None:
        self.__groups: DefaultDict[int, Set[str]] = defaultdict(lambda: set())

    def __delete(self, group_id: int, url: str) -> None:
        if url in self.__groups[group_id]:
            self.__groups[group_id].remove(url)

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
        """如果添加成功，返回True

        Args:
            group_id (int): _description_
            url (str): _description_

        Returns:
            bool: _description_
        """
        if url not in self.__groups[group_id]:
            self.__groups[group_id].add(url)
            asyncio.get_running_loop().call_later(
                DEFAULT_CACHE_TIME, self.__delete, group_id, url
            )
            return True
        return False


class ParserManager:
    def __init__(self) -> None:
        self.__trie: StringTrie[str, Tuple[Callable, str]] = StringTrie()
        self.__url_cache = GroupCache()
        self.__result_cache: Dict[str, Tuple[Message, str]] = {}

    def __delete(self, url: str) -> None:
        if url in self.__result_cache:
            del self.__result_cache[url]

    async def __parser(
        self, func: Callable, ttl: float, url: str, group_id: int
    ) -> Optional[Message]:
        if cache := self.__result_cache.get(url):
            ret, ret_url = cache
        else:
            try:
                ret, ret_url = await func(url)
            except Exception as e:
                logger.warning(f"解析 url 时发生错误：{e}")
                return None
            ret = Message(ret)
            if ttl is not None:
                self.__result_cache[url] = (ret, ret_url)
                asyncio.get_running_loop().call_later(ttl, self.__delete, url)
        # 检测解析后的最终url
        if self.__url_cache.add(group_id=group_id, url=ret_url):
            # 添加输入的url
            self.__url_cache.add(group_id=group_id, url=url)
            return ret
        return None

    def __call__(
        self, task_name: str, startswith: Tuple[str, ...], ttl: float = None
    ) -> Any:
        def add_parser(func):
            for starts_url in startswith:
                self.__trie[starts_url] = (
                    partial(self.__parser, func=func, ttl=ttl),
                    task_name,
                )

        return add_parser

    async def get_parser(
        self, urls: List[str], group_id: int
    ) -> Set[Callable[[str], Any]]:
        ret = []
        for url in urls:
            url = url.replace("\/", "/")
            if url.startswith(ALIAS_DOMAIN):
                url = await get_url(url)
            url = url.rstrip("&")
            if url.startswith("http:"):
                url = url.replace("http:", "https:", 1)
            # cd没过，跳过
            if self.__url_cache.check(group_id=group_id, url=url):
                continue
            _, func = self.__trie.longest_prefix(url)
            if func and check_task(group_id=group_id, task_name=func[1]):
                ret.append(partial(func[0], url=url, group_id=group_id))
        return ret

    async def do_parse(self, parsers: List[Tuple[Callable, str]]) -> List[Message]:
        return await asyncio.gather(*[parser() for parser in parsers])


parser_manager = ParserManager()
