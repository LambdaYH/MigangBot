from datetime import datetime

from migang.core.utils.langchain_tool import nb_langchain_tool


@nb_langchain_tool
def get_current_time() -> str:
    """获取当前时间工具，返回当前时间字符串"""
    current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S %A")
    return f"当前时间是: {current_time}"
