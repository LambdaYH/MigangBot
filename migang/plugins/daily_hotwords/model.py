from typing import Optional
from datetime import time  # noqa

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from nonebot_plugin_datastore import get_plugin_data

Model = get_plugin_data().Model


class Schedule(Model):
    """定时发送"""

    __table_args__ = (
        UniqueConstraint(
            "bot_id",
            "platform",
            "group_id",
            "guild_id",
            "channel_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[str] = mapped_column(String(64))
    platform: Mapped[str] = mapped_column(String(32))
    group_id: Mapped[str] = mapped_column(String(64), default="")
    guild_id: Mapped[str] = mapped_column(String(64), default="")
    channel_id: Mapped[str] = mapped_column(String(64), default="")
    time: Mapped[Optional["time"]]
    """ UTC 时间 """
