from typing import Any, Annotated

import ujson
from nonebot.params import Depends
from nonebot.typing import T_State
from nonebot_plugin_alconna import UniMessage
from nonebot.adapters import Bot, Event, Message
from nonebot.consts import PREFIX_KEY, CMD_ARG_KEY


async def _uni_cmd_arg(bot: Bot, event: Event, state: T_State) -> UniMessage:
    return await UniMessage.generate(
        message=state[PREFIX_KEY][CMD_ARG_KEY], event=event, bot=bot
    )


def UniCmdArg() -> Any:
    """消息命令参数"""
    return Depends(_uni_cmd_arg)


async def serialize_message(bot: Bot, event: Event, msg: Message | UniMessage) -> str:
    if isinstance(msg, Message):
        msg = await UniMessage.generate(message=msg, bot=bot, event=event)
    return


def deserialize_message(msg: str) -> UniMessage:
    return ujson.load(msg)


__all__ = ["UniCmdArg"]
