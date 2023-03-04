import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from .model import Aircon

R = 8.314  # 理想气体常数
i = 6  # 多分子气体自由度
vgas = 22.4  # 气体摩尔体积
unit_volume = 2  # 每人体积
aircon_off = 0.05  # 关空调后每秒温度变化量
ac_volume = [0.178, 0.213, 0.267]  # 每秒进风量
powers = [5000, 6000, 7500]  # 功率
volume_text = ["低", "中", "高"]

ac_central_power = 7500
ac_central_windrate = 0.577
ac_central_unit_volume = 100

AIRCON_HOME = 0
AIRCON_CENTRAL = 1


def sgn(diff):
    return 1 if diff > 0 else -1 if diff < 0 else 0


def now_second():
    return int(
        (datetime.datetime.now() - datetime.datetime(1970, 1, 1)).total_seconds()
    )


def get_temp(N, n, setting, prev, T, power):
    direction = sgn(setting - prev)
    threshold = power / (n * 1000 / vgas) / (i / 2) / R
    cps = power / (N * 1000 / vgas) / (i / 2) / R

    if (abs(setting - prev) - threshold) >= cps * T:
        new_temp = prev + direction * cps * T
    else:
        t1 = max(0, int((abs(setting - prev) - threshold) / cps))
        temp1 = prev + direction * cps * t1
        new_temp = (1 - n / N) ** (T - t1 - 1) * (temp1 - setting) + setting
    return round(new_temp, 1)


def print_aircon(aircon: Aircon):
    text = (
        f"当前风速{volume_text[aircon.wind_rate]}\n"
        if (aircon.is_on and aircon.ac_type == AIRCON_HOME)
        else ""
    )

    text += f"""
当前设置温度 {aircon.set_temp} °C
当前群里温度 {round(aircon.now_temp,1)} °C
当前环境温度 {aircon.env_temp} °C""".strip()

    return text


async def get_aircon(session: AsyncSession, group_id: int):
    return await session.scalar(
        statement=select(Aircon).where(Aircon.group_id == group_id)
    )


def install_aircon(
    session: AsyncSession, group_id: int, num_member: int, set_temp=26, now_temp=33
):
    aircon = Aircon(
        group_id=group_id,
        env_temp=now_temp,
        now_temp=now_temp,
        set_temp=set_temp,
        last_update=now_second(),
        volume=max(num_member * unit_volume, 20),
        wind_rate=0,
        balance=0,
        ac_type=AIRCON_HOME,
        is_on=True,
    )
    session.add(aircon)
    return aircon


def update_aircon(
    session: AsyncSession,
    aircon: Aircon,
    ison: Optional[bool] = None,
    settemp: Optional[int] = None,
    envtemp: Optional[float] = None,
    actype: Optional[int] = None,
    windrate: Optional[int] = None,
):
    new_update = now_second()
    timedelta = new_update - aircon.last_update
    if aircon.is_on:
        power = powers[aircon.wind_rate]
        wind_rate = ac_volume[aircon.wind_rate]
        if aircon.ac_type == AIRCON_HOME:
            power = powers[aircon.wind_rate]
            wind_rate = ac_volume[aircon.wind_rate]
        elif aircon.ac_type == AIRCON_CENTRAL:
            power = (aircon.volume // ac_central_unit_volume + 1) * ac_central_power
            wind_rate = (
                aircon.volume // ac_central_unit_volume + 1
            ) * ac_central_windrate

        new_temp = get_temp(
            aircon.volume,
            wind_rate,
            aircon.set_temp,
            aircon.now_temp,
            timedelta,
            power,
        )
        aircon.now_temp = new_temp
        aircon.last_update = new_update
    else:
        direction = sgn(aircon.env_temp - aircon.now_temp)
        new_temp = aircon.now_temp + direction * timedelta * aircon_off
        if (aircon.env_temp - aircon.now_temp) * (
            aircon.env_temp - new_temp
        ) < 0:  # 过头了
            new_temp = aircon.env_temp
        aircon.now_temp = new_temp
        aircon.last_update = new_update
    if ison is not None:
        aircon.is_on = ison
    if settemp is not None:
        aircon.set_temp = settemp
    if windrate is not None:
        aircon.wind_rate = windrate
    if actype is not None:
        aircon.ac_type = actype
    if envtemp is not None:
        aircon.env_temp = envtemp
    session.add(aircon)
