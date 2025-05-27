from typing import List


class LangChainToolManager:
    """LangChain工具管理器，支持动态注册工具"""

    def __init__(self):
        self.tools = []

    def register_tool(self, tool_obj):
        self.tools.append(tool_obj)

    def get_tools(self) -> List:
        """获取所有工具"""
        return self.tools


# 全局工具管理器实例
tool_manager = LangChainToolManager()
