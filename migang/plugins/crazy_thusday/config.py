import asyncio
from pathlib import Path
from typing import Dict, List, Union

import anyio
import httpx
from nonebot.log import logger
from pydantic import Extra, BaseModel
from nonebot import get_driver, get_plugin_config

from migang.core.utils import http_utils

try:
    import ujson as json
except ModuleNotFoundError:
    import json


class PluginConfig(BaseModel, extra=Extra.ignore):
    crazy_path: Path = Path() / "data" / "crazy_thusday"


driver = get_driver()
crazy_config: PluginConfig = get_plugin_config(PluginConfig)
crazy_config.crazy_path.mkdir(exist_ok=True, parents=True)


class DownloadError(Exception):
    pass


class ResourceError(Exception):
    pass


async def download_url(url: str) -> Union[httpx.Response, None]:
    async with httpx.AsyncClient() as client:
        for i in range(3):
            try:
                response = await client.get(url, follow_redirects=True)
                if response.status_code != 200:
                    continue
                return response
            except Exception as e:
                logger.warning(f"Error occured when downloading {url}, {i+1}/3: {e}")

    logger.warning("Abort downloading")
    return None


async def post_check() -> None:
    """
    Get the latest version of post.json from repo
    If failed and post dosen't exists, raise exception
    Otherwise just abort downloading
    """
    json_path: Path = crazy_config.crazy_path / "post.json"

    url = "https://raw.githubusercontent.com/MinatoAquaCrews/nonebot_plugin_crazy_thursday/master/nonebot_plugin_crazy_thursday/post.json"

    try:
        response = await http_utils.request_gh(url)
    except Exception as e:
        logger.warning("获取crary thusday失败")
        response = None

    if response is None:
        if not json_path.exists():
            logger.warning("Crazy Thursday resource missing! Please check!")
    else:
        docs: Dict[str, Union[float, List[str]]] = response.json()
        version = docs.get("version")

        async with await anyio.open_file(json_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(docs, ensure_ascii=False, indent=4))
            logger.info(
                f"Get the latest Crazy Thursday posts from repo, version: {version}"
            )


@driver.on_startup
async def _():
    asyncio.create_task(post_check())
