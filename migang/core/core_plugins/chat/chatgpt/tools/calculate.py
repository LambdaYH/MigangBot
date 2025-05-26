from langchain_core.tools import tool


@tool
def calculate(expression: str) -> str:
    """简单计算器工具，支持+、-、*、/、**等基本运算"""
    try:
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "错误：表达式包含不安全的字符"
        result = eval(expression)
        return f"计算结果: {expression} = {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"
