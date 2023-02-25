from enum import unique, IntEnum


@unique
class Permission(IntEnum):
    """用户与群权限"""

    BLACK: int = 1
    BAD: int = 2
    NORMAL: int = 3
    GOOD: int = 4
    EXCELLENT: int = 5


BLACK = Permission.BLACK
BAD = Permission.BAD
NORMAL = Permission.NORMAL
GOOD = Permission.GOOD
EXCELLENT = Permission.EXCELLENT
