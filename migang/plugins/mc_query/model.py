from typing import Optional

from nonebot_plugin_datastore import get_plugin_data
from sqlmodel import Field

Model = get_plugin_data().Model


class McServerGroup(Model, table=True):
    __table_args__ = {"extend_existing": True}

    group_id: int = Field(primary_key=True)
    name: str
    host: str
    port: Optional[int]
    sv_type: str


class McServerPrivate(Model, table=True):
    __table_args__ = {"extend_existing": True}

    user_id: int = Field(primary_key=True)
    name: str
    host: str
    port: Optional[int]
    sv_type: str
