from datetime import datetime

from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from nonebot_plugin_datastore import get_plugin_data

Model = get_plugin_data().Model


class EorzeanZhanbuRecorder(Model):
    __table_args__ = {"extend_existing": True}

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    luck: Mapped[int]
    yi: Mapped[str]
    ji: Mapped[str]
    dye: Mapped[str]
    append_msg: Mapped[str]
    basemap: Mapped[str]
    time: Mapped[datetime] = mapped_column(default=datetime.now())
