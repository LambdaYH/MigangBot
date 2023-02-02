from typing import List
from pydantic import BaseModel
from enum import Enum, unique


@unique
class PluginStatus(Enum):
    enabled: int = 0
    disabled: int = 1
    group_disabled: int = 2
    not_authorized: int = 3


class Item(BaseModel):
    plugin_name: str
    status: PluginStatus


class PluginList(BaseModel):
    plugin_type: str
    icon: str
    logo: str
    items: List[Item]
