import os
import random
import inspect
import importlib
import traceback
from typing import Any, Dict, List, Optional

from nonebot.log import logger
from langchain_core.tools import BaseTool, tool

from migang.core import get_config

TOOLS_DIR = os.path.join(os.path.dirname(__file__), "tools")


class LangChainToolManager:
    """LangChain工具管理器，将原有扩展转换为langchain tools"""

    def __init__(self):
        self.tools = []
        self._auto_register_tools()

    def _auto_register_tools(self):
        for filename in os.listdir(TOOLS_DIR):
            if filename.endswith(".py") and not filename.startswith("_"):
                module_name = (
                    f"migang.core.core_plugins.chat.chatgpt.tools.{filename[:-3]}"
                )
                module = importlib.import_module(module_name)
                for name, obj in inspect.getmembers(module):
                    if isinstance(obj, BaseTool):
                        self.tools.append(obj)

    def get_tools(self) -> List:
        """获取所有工具"""
        return self.tools


# 全局工具管理器实例
tool_manager = LangChainToolManager()
