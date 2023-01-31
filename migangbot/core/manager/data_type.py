from enum import Enum, unique


@unique
class LimitType(Enum):
    user = 0
    group = 1


@unique
class CheckType(Enum):
    private = 0
    group = 1
    all = 2


@unique
class CountPeriod(Enum):
    hour = 0
    day = 1
    week = 2
    month = 3
    year = 4
