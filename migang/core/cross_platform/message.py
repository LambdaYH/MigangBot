from typing import Any, Annotated

from nonebot.typing import T_State
from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import UniMessage
from nonebot.params import Depends, CommandArg
from nonebot.consts import PREFIX_KEY, CMD_ARG_KEY


async def _uni_cmd_arg(bot: Bot, event: Event, state: T_State) -> UniMessage:
    return await UniMessage.generate(
        message=state[PREFIX_KEY][CMD_ARG_KEY], event=event, bot=bot
    )


def UniCmdArg() -> Any:
    """消息命令参数"""
    return Depends(_uni_cmd_arg)


__all__ = ["UniCmdArg"]
