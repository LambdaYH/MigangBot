import asyncio
from pathlib import Path
from typing import Dict, Iterable, Optional, Union

import aiohttp
import anyio
from fake_useragent import UserAgent
from nonebot.log import logger
from tenacity import retry, stop_after_attempt, wait_random


async def async_download_files(
    urls: Union[Iterable[str], str],
    path: Union[str, Path],
    concurrency_limit: int = 10,
    names: Union[str, Iterable[str]] = None,
    params: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
    cookies: Optional[str] = None,
    timeout: Optional[int] = 30,
    stream: bool = False,
) -> int:
    """异步下载文件到指定路径

    url为str时，names也必须为str，反之亦然

    Args:
        urls (Union[Iterable[str], str]): 单个url或urls
        path (Union[str, Path]): 下载的目的文件或路径，仅单个url可以为str
        concurrency_limit (int, optional): 并发限制，默认不限制. Defaults to 10.
        names (Union[str, Iterable[str]], optional): 名字数与链接数相等，若名字为空，则从链接中提取，若目的文件和名字同时被指定，以名字为主. Defaults to None.
        params (Optional[Dict[str, str]], optional): 参数. Defaults to None.
        headers (Optional[Dict[str, str]], optional): 请求头. Defaults to None.
        cookies (Optional[str], optional): cookies. Defaults to None.
        timeout (Optional[int], optional): 超时时间. Defaults to 30.
        stream (bool, optional): 是否流式下载，适合大文件. Defaults to False.

    Raises:
        Exception: 参数类型不匹配时

    Returns:
        int: 下载成功的个数
    """
    if isinstance(path, str):
        path = Path(path)
    if path.suffix and isinstance(urls, Iterable):
        raise Exception("当path为单个文件时，urls不可为多个url")
    if isinstance(urls, str):
        path = path.parent
        if isinstance(names, str):
            names = (names,)
        elif names:
            raise Exception("当url为字符串时，names也必须为字符串")
        else:
            names = (Path(urls).name,)
        urls = (urls,)
    path.mkdir(parents=True, exist_ok=True)
    if names and (len(names) != len(urls)):
        raise Exception("名字与链接数不相等")
    if not names:
        names = [Path(url).name for url in urls]
    if not headers:
        headers = {"user-agent": UserAgent(browsers=["edge", "chrome"]).random}

    sem = asyncio.Semaphore(concurrency_limit)

    @retry(wait=wait_random(min=5, max=20), stop=stop_after_attempt(3))
    async def download(client: aiohttp.ClientSession, url: str, file: Path):
        async with sem:
            r = await client.get(
                url,
                params=params,
                headers=headers,
                cookies=cookies,
                timeout=timeout,
                allow_redirects=True,
            )
        async with await anyio.open_file(file, "wb") as f:
            if not stream:
                await f.write(await r.read())
            else:
                async for data in r.content.iter_chunked(10240):
                    await f.write(data)
        logger.info(f"{url} 已下载至 {file}")

    count = 0
    async with aiohttp.ClientSession() as client:
        for i, e in enumerate(
            await asyncio.gather(
                *[
                    download(client=client, url=url, file=path / names[i])
                    for i, url in enumerate(urls)
                ],
                return_exceptions=True,
            )
        ):
            if not e:
                count += 1
            else:
                logger.warning(f"{urls[i]} 下载失败: {e}")
    return count
