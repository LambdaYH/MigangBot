from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from nonebot_plugin_datastore import get_plugin_data

Model = get_plugin_data().Model


class Aircon(Model):
    __table_args__ = {"extend_existing": True}

    group_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    env_temp: Mapped[int]
    now_temp: Mapped[float]
    set_temp: Mapped[int]
    last_update: Mapped[int]
    volume: Mapped[int]
    wind_rate: Mapped[int]
    balance: Mapped[int]
    ac_type: Mapped[int]
    is_on: Mapped[bool]
