#  暂时不启用
import re
import base64
import secrets
from io import BytesIO
from typing import Tuple
from urllib.parse import urljoin, urlparse

import httpx
import requests
from PIL import Image
from lxml import etree
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment

from migang.utils.image import pic_to_b64

from .utils import parser_manager


async def get_meta_data(url) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

        # 检查并设置正确的编码
        content_type = response.headers.get("content-type", "")
        charset_match = re.search(r"charset=([\w-]+)", content_type)
        encoding = (
            charset_match.group(1) if charset_match else response.encoding or "utf-8"
        )

        tree = etree.HTML(response.content.decode(encoding))

        meta_tags = tree.xpath("//meta")
        meta = {}
        for tag in meta_tags:
            name = tag.get("name") or tag.get("property")
            content = tag.get("content")
            if name and content:
                meta[name] = content

        url_obj = urlparse(url)
        meta["url"] = url_obj.netloc.replace("www.", "").capitalize()
        logger.info(f"获取到元数据: {meta}")
        return meta
    except Exception as e:
        logger.warning(f"无法获取链接元数据：{url}，{e}", exc_info=True)
        return None


def is_valid_twitter_post_url(url):
    twitter_post_pattern = r"^https?://(?:www\.)?twitter\.com/\w+/status/\d+$"
    return re.match(twitter_post_pattern, url) is not None


def is_twitter_profile_url(url):
    twitter_profile_pattern = r"^https?://(?:www\.)?twitter\.com/\w+$"
    return re.match(twitter_profile_pattern, url) is not None


def get_tweet_web_meta(url):
    return None


def get_twitter_user_info_web_meta(url):
    return None


async def get_web_preview(url) -> Message:
    try:
        web_meta = None
        if is_valid_twitter_post_url(url):
            web_meta = get_tweet_web_meta(url)
        elif is_twitter_profile_url(url):
            web_meta = get_twitter_user_info_web_meta(url)
        else:
            web_meta = await get_meta_data(url)

        if web_meta is None:
            return None, url

        standard_data = {
            "url": url,
            "title": (
                web_meta.get("og:title")
                or web_meta.get("twitter:title")
                or web_meta.get("title")
            ),
            "imageUrl": (
                web_meta.get("og:image")
                or web_meta.get("twitter:image:src")
                or web_meta.get("twitter:image")
                or web_meta.get("image")
            ),
            "alt": (
                web_meta.get("og:image:alt")
                or web_meta.get("twitter:description")
                or web_meta.get("description")
            ),
            "description": (
                web_meta.get("og:description")
                or web_meta.get("twitter:description")
                or web_meta.get("description")
            ),
            "site_name": (
                web_meta.get("og:site_name")
                or web_meta.get("twitter:site")
                or web_meta.get("url")
            ),
        }
        return standard_data.get("title", None), url
    except Exception as e:
        logger.warning(f"链接解析出错：{e}", exc_info=True)
        return None, url


@parser_manager(task_name="url_default_parse")
async def get_url_preview(url: str) -> Tuple[Message, str]:
    return await get_web_preview(url)
