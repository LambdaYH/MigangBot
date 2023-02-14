from enum import Enum, unique


@unique
class Permission(Enum):
    """用户与群权限"""

    BLACK: int = 1
    BAD: int = 2
    NORMAL: int = 3
    GOOD: int = 4
    EXCELLENT: int = 5

    def __eq__(self, __o: object) -> bool:
        return self._value_ == __o._value_

    def __ne__(self, __o: object) -> bool:
        return self._value_ != __o._value_

    def __gt__(self, __o: object) -> bool:
        return self._value_ > __o._value_

    def __ge__(self, __o: object) -> bool:
        return self._value_ >= __o._value_

    def __lt__(self, __o: object) -> bool:
        return self._value_ < __o._value_

    def __le__(self, __o: object) -> bool:
        return self._value_ <= __o._value_


BLACK = Permission.BLACK
BAD = Permission.BAD
NORMAL = Permission.NORMAL
GOOD = Permission.GOOD
EXCELLENT = Permission.EXCELLENT
