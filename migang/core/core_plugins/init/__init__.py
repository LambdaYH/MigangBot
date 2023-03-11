"""初始化插件各数据
"""

import asyncio

from nonebot import get_driver

from .command_check import check_command
from .init_plugin_cd import init_plugin_cd
from .init_plugin_info import init_plugin_info
from .init_plugin_task import init_plugin_task
from .init_plugin_count import init_plugin_count
from .init_plugin_config import init_plugin_config
from .init_font import load_font


@get_driver().on_startup
async def _():
    await asyncio.gather(
        *[
            init_plugin_info(),
            init_plugin_config(),
            init_plugin_count(),
            init_plugin_task(),
            load_font(),
        ]
    )
    init_plugin_cd()
    check_command()
