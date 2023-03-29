import secrets
from typing import Tuple

from nonebot.adapters.onebot.v11 import Message, MessageSegment

from .utils import parser_manager


@parser_manager(
    task_name="url_parse_github_repo_card", startswith=("https://github.com",)
)
async def get_github_repo_card(url: str) -> Tuple[Message, str]:
    url = url.lstrip("https://")
    info = url[url.find("/") + 1 :].split("/")
    if len(info) < 2:
        raise Exception("非Github仓库链接")
    return (
        MessageSegment.image(
            f"https://opengraph.githubassets.com/{secrets.token_urlsafe(16)}/{info[0]}/{info[1]}"
        ),
        f"https://github.com/{info[0]}/{info[1]}",
    )
