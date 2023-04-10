"""初始化插件各数据
"""

import asyncio

from nonebot import logger, get_driver
from nonebot.utils import run_sync, is_coroutine_callable

from migang.core.utils import config_operation

from .init_font import load_font
from .command_check import check_command
from .init_plugin_cd import init_plugin_cd
from .init_plugin_info import init_plugin_info
from .init_plugin_task import init_plugin_task
from .init_plugin_count import init_plugin_count
from .init_plugin_config import init_plugin_config


@get_driver().on_startup
async def _():
    # 执行初始化前的函数
    cors = [
        func() if is_coroutine_callable(func) else run_sync(func)()
        for func in config_operation._pre_init_manager_func
    ]
    if cors:
        try:
            await asyncio.gather(*cors)
        except Exception as e:
            logger.error(f"执行初始化前的函数出错：{e}")

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

    # 执行初始化后的函数
    cors = [
        func() if is_coroutine_callable(func) else run_sync(func)()
        for func in config_operation._post_init_manager_func
    ]
    if cors:
        try:
            await asyncio.gather(*cors)
        except Exception as e:
            logger.error(f"执行初始化后的函数出错：{e}")
