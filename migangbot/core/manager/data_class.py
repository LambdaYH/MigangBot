from enum import Enum, unique


@unique
class LimitType(Enum):
    """用于CD限制与调用次数限制，限制检测的对象为用户或整个群"""

    user = 0
    """检测user_id
    """
    group = 1
    """检测group_id
    """


@unique
class CheckType(Enum):
    """用于CD限制与调用次数限制，限制检测的会话为私聊或群聊或全部"""

    private = 0
    """私聊
    """
    group = 1
    """群聊
    """
    all = 2
    """私聊+群聊
    """


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
    """仅群聊可用
    """
    Private = 1
    """仅私聊可用
    """
    All = 2
    """私聊+群聊都可用
    """
    SuperUser = 3
    """仅超级用户可用
    """
    GroupAdmin = 4
    """仅群主+管理员可用
    """
