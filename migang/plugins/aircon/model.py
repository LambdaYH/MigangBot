from sqlmodel import Field
from nonebot_plugin_datastore import get_plugin_data


Model = get_plugin_data().Model


class Aircon(Model, table=True):
    __table_args__ = {"extend_existing": True}

    group_id: int = Field(primary_key=True)
    env_temp: int
    now_temp: float
    set_temp: int
    last_update: int
    volume: int
    wind_rate: int
    balance: int
    ac_type: int
    is_on: bool
