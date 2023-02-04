from enum import Enum, unique


@unique
class LimitType(Enum):
    """用于CD限制与调用次数限制，限制检测的对象为用户或整个群"""

    user = 0
    group = 1


@unique
class CheckType(Enum):
    """用于CD限制与调用次数限制，限制检测的会话为私聊或群聊或全部"""

    private = 0
    group = 1
    all = 2


@unique
class CountPeriod(Enum):
    """用于调用次数限制，限制检测的周期"""

    hour = 0
    day = 1
    week = 2
    month = 3
    year = 4


@unique
class PluginType(Enum):
    """该类不具备实质用途，仅用于生成帮助文件"""

    Group = 0
    Private = 1
    All = 2
    SuperUser = 3
    GroupAdmin = 4
