from typing import Any, Dict, List

from sqlalchemy import JSON, String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from nonebot_plugin_datastore import get_plugin_data

Model = get_plugin_data().Model


class Schedule(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    group_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    type: Mapped[str] = mapped_column(String(255))
    param: Mapped[Dict[str, Any]] = mapped_column(JSON)
    content: Mapped[List[Dict[str, Any]]] = mapped_column(JSON)
