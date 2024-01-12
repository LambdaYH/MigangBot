from typing import Annotated

from nonebot.params import Depends
from nonebot.typing import T_State
from nonebot.adapters import Bot, Event

from .session import MigangSession


def get_session(bot: Bot, event: Event) -> MigangSession:
    """获取migangsession"""
    return MigangSession.get_session(bot=bot, event=event)


Session = Annotated[MigangSession, Depends(get_session)]
