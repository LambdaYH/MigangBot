from datetime import datetime

from lunarcalendar import Solar, Converter


def is_chinese_new_year():
    today = datetime.now()

    lunar_today = Converter.Solar2Lunar(Solar(today.year, today.month, today.day))

    return lunar_today.month == 1 and lunar_today.day == 1


def is_solor_new_year():
    today = datetime.now()

    return today.month == 1 and today.day == 1


def is_new_year():
    return is_chinese_new_year() or is_solor_new_year()
