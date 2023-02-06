from typing import Dict, Any, Optional

from nonebot.adapters import Bot

from migangbot.core.models import NickName


@Bot.on_called_api
async def handle_api_result(
    bot: Bot,
    exception: Optional[Exception],
    api: str,
    data: Dict[str, Any],
    result: Any,
):
    # 将群成员昵称用昵称系统替换，保留群员卡片
    if api == "get_group_member_info":
        pass
