import httpx
import nonebot
from nonebot import get_driver
from nonebot.log import logger

# https://github.com/lambdayh/hub-proxy 自建一个
GH_PROXY_URL: str = ""
GH_PROXY_HEADERS = {}


def is_empty_or_none(s):
    return s is None or s == ""


@get_driver().on_startup
async def _():
    config = nonebot.get_driver().config
    global GH_PROXY_URL
    global GH_PROXY_HEADERS
    try:
        # 初始化 GH_PROXY_URL
        GH_PROXY_URL = config.gh_proxy_url
        if not is_empty_or_none(GH_PROXY_URL) and not GH_PROXY_URL.endswith("/"):
            GH_PROXY_URL = GH_PROXY_URL + "/"
        # 初始化 GH_PROXY_HEADERS
        try:
            if not is_empty_or_none(config.gh_proxy_headers):
                try:
                    GH_PROXY_HEADERS = dict(
                        item.split(":") for item in config.gh_proxy_headers.split(",")
                    )
                except ValueError as e:
                    logger.error(f"无法解析 gh_proxy_headers: {e}")
                    GH_PROXY_HEADERS = {}
        except AttributeError as e:
            logger.info("未配置gh代理请求头，跳过")
            GH_PROXY_HEADERS = {}
    except AttributeError as e:
        logger.info("未配置gh代理，跳过")
        GH_PROXY_URL = None
        GH_PROXY_HEADERS = {}


async def request_gh(url: str):
    if is_empty_or_none(url):
        logger.warning("链接不得为空")
        return None

    # 拼接代理 URL
    full_url = get_gh_url(url)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(full_url, headers=GH_PROXY_HEADERS, timeout=30)
            response.raise_for_status()
            return response
    except httpx.RequestError as e:
        logger.warning(f"请求 {full_url} 异常: {e}")
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP状态码错误: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.warning(f"未知异常: {e}")

    raise Exception(f"请求 {full_url} 失败")


def get_gh_url(url: str):
    if is_empty_or_none(url):
        logger.warning("链接不得为空")
        return None

    # 拼接代理 URL
    return GH_PROXY_URL + url if GH_PROXY_URL else url


def get_gh_headers():
    return GH_PROXY_HEADERS
