from datetime import datetime

from nonebot_plugin_datastore import get_plugin_data
from sqlmodel import Field

Model = get_plugin_data().Model


class EorzeanZhanbuRecorder(Model, table=True):
    __table_args__ = {"extend_existing": True}

    user_id: int = Field(primary_key=True)
    luck: int
    yi: str
    ji: str
    dye: str
    append_msg: str
    basemap: str
    time: datetime = Field(default=datetime.now())
