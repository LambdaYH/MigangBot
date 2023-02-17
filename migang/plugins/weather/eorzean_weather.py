""" 艾欧泽亚天气预报
"""
import time
from typing import Optional
from . import eorzean_weather_data


def int_overflow(n: int):
    """模拟 JavaScript 的溢出"""
    return n & (2**32 - 1)


def unsigned_right_shitf(n: int, i: int):
    """模拟 JavaScript 的无符号右移"""
    return (n & (2**32 - 1)) >> i


def forecastTarget(date: int):
    """预测"""
    bell = date // 175
    increment = (bell + 8 - (bell % 8)) % 24

    totalDays = date // 4200

    calcBase = totalDays * 100 + increment

    step1 = int_overflow((calcBase << 11) ^ calcBase)
    step1 = unsigned_right_shitf(step1, 0)
    step2 = unsigned_right_shitf(step1, 8) ^ step1
    step2 = unsigned_right_shitf(step2, 0)

    return step2 % 100


def calc_eorzean_weather(date: int, location: str) -> str:
    """计算艾欧泽亚天气"""
    if eorzean_weather_data.location_idx.get(location):
        weather_rate = eorzean_weather_data.weather_rate_idx[
            eorzean_weather_data.location_idx[location]["weather_rate"]
        ]
    else:
        raise f"No weather data of {location}"

    target = forecastTarget(date)

    for rate in weather_rate:
        if target < rate["rate"]:
            weather = eorzean_weather_data.weather_idx[rate["weather"]]
            return weather


def getEorzeaHour(unixSeconds):
    bell = (unixSeconds / 175) % 24
    return int(bell)


def next_weather_time(date: int, count: int) -> int:
    """计算下一个天气时段所剩时间(格式mm:ss)"""
    # 计算当前时间戳所属的区间(以4200s为一个完整的周期，艾欧泽亚日)
    increament = (date + 1400 - (date % 1400)) % 4200
    cur_time = date % 4200
    if increament > cur_time:
        left_sec = increament - cur_time
    else:
        left_sec = 4200 - cur_time
    left_sec += 1400 * count

    return left_sec


def get_eorzean_weather(location: str) -> Optional[str]:
    """艾欧泽亚天气

    利姆萨·罗敏萨
    当前天气：碧空
    还剩12分55秒切换到天气：阴云
    """
    try:
        if eorzean_weather_data.alter_name.get(location):
            location = eorzean_weather_data.alter_name.get(location)
        str_data = f"[{location}]\n"

        date = int(time.time())
        weather = calc_eorzean_weather(date, location)
        str_data += f"当前天气：{weather}"
        for i in range(9):
            next_date = date + 1400 * (i + 1)
            furWeather = calc_eorzean_weather(next_date, location)
            next_time = next_weather_time(date, i) + date
            str_data += f"\nLT:{time.strftime('%m-%d %H:%M:%S', time.localtime(next_time))}  ET:{getEorzeaHour(next_time):02}:00 -> {furWeather}"
        return str_data
    except:
        return None
