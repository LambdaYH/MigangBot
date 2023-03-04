from typing import Optional
from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from nonebot_plugin_datastore import get_plugin_data

Model = get_plugin_data().Model


class McServerGroup(Model):
    __table_args__ = {"extend_existing": True}

    group_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str]
    host: Mapped[str]
    port: Mapped[Optional[int]]
    sv_type: Mapped[str]


class McServerPrivate(Model):
    __table_args__ = {"extend_existing": True}

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str]
    host: Mapped[str]
    port: Mapped[Optional[int]]
    sv_type: Mapped[str]
