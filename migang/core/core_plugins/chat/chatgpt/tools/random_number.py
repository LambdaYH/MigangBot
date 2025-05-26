import random

from langchain_core.tools import tool


@tool
def generate_random_number(min_val: int = 1, max_val: int = 100) -> str:
    """生成随机数工具，返回指定范围的随机整数"""
    if min_val > max_val:
        min_val, max_val = max_val, min_val
    result = random.randint(min_val, max_val)
    return f"随机数生成结果: {result} (范围: {min_val}-{max_val})"
