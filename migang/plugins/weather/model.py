from enum import IntEnum
from typing import List, Optional

from pydantic import BaseModel
from nonebot.compat import PYDANTIC_V2, ConfigDict


class Now(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(extra="allow")
    else:

        class Config:
            extra = "allow"

    obsTime: str
    temp: str
    icon: str
    text: str
    windScale: str
    windDir: str
    humidity: str
    precip: str
    vis: str


class NowApi(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(extra="allow")
    else:

        class Config:
            extra = "allow"

    code: str
    now: Now


class Daily(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(extra="allow")
    else:

        class Config:
            extra = "allow"

    fxDate: str
    week: Optional[str] = None
    date: Optional[str] = None
    tempMax: str
    tempMin: str
    textDay: str
    textNight: str
    iconDay: str
    iconNight: str


class DailyApi(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(extra="allow")
    else:

        class Config:
            extra = "allow"

    code: str
    daily: List[Daily]


class Air(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(extra="allow")
    else:

        class Config:
            extra = "allow"

    category: str
    aqi: str
    pm2p5: str
    pm10: str
    o3: str
    co: str
    no2: str
    so2: str
    tag_color: Optional[str] = None


class AirApi(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(extra="allow")
    else:

        class Config:
            extra = "allow"

    code: str
    now: Optional[Air] = None


class Warning(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(extra="allow")
    else:

        class Config:
            extra = "allow"

    title: str
    type: str
    pubTime: str
    text: str


class WarningApi(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(extra="allow")
    else:

        class Config:
            extra = "allow"

    code: str
    warning: Optional[List[Warning]] = None


class Hourly(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(extra="allow")
    else:

        class Config:
            extra = "allow"

    fxTime: str
    hour: Optional[str] = None
    temp: str
    icon: str
    text: str
    temp_percent: Optional[str] = None


class HourlyApi(BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(extra="allow")
    else:

        class Config:
            extra = "allow"

    code: str
    hourly: List[Hourly]


class HourlyType(IntEnum):
    current_12h = 1
    current_24h = 2
