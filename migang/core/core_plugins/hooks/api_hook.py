from typing import Any, Dict, Optional

from nonebot.adapters import Bot

from migang.core.models import NickName


@Bot.on_called_api
async def handle_api_result(
    bot: Bot,
    exception: Optional[Exception],
    api: str,
    data: Dict[str, Any],
    result: Any,
):
    # 将昵称用昵称系统替换，保留群员卡片
    if (api == "get_group_member_info" or api == "get_stranger_info") and (
        name := await NickName.filter(user_id=data["user_id"]).first()
    ):
        result["nickname"] = name.nickname
