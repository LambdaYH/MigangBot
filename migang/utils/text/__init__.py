from typing import Union

from .filter import filt_message  # noqa


def is_number(s: Union[int, str]) -> bool:
    """
    说明:
        检测 s 是否为数字
    参数:
        :param s: 文本
    """
    if isinstance(s, int):
        return True
    try:
        float(s)
        return True
    except ValueError:
        pass
    try:
        import unicodedata

        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass
    return False
