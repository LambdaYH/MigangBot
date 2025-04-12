from urllib.parse import urljoin

import httpx
import nonebot
from nonebot import get_driver
from nonebot.log import logger

# https://github.com/LambdaYH/migangbot-api 自建一个，用于将一些服务转移到服务器上以加快访问速度

MIGANGBOT_API: str = None
IS_USE_API = False


def is_empty_or_none(s):
    return s is None or s == ""


client = httpx.AsyncClient()


@get_driver().on_startup
async def _():
    config = nonebot.get_driver().config
    global MIGANGBOT_API
    global IS_USE_API
    try:
        MIGANGBOT_API = config.migangbot_api
        IS_USE_API = not is_empty_or_none(MIGANGBOT_API)
        logger.info("已配置migangbot_api，使用api模式")
    except AttributeError as e:
        pass


def is_use_api():
    return IS_USE_API


async def get_api_result(api: str, **kwargs):
    try:
        r = await client.get(urljoin(MIGANGBOT_API, api), params=kwargs, timeout=30)
        r.raise_for_status()
        return r.json()["data"]
    except Exception as e:
        logger.error(
            f"请求migangbot-api发生错误---method: get\napi: {api}\nparam: {kwargs}\n{e}"
        )
    return None
