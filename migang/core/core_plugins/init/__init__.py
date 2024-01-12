"""初始化插件各数据
"""

import asyncio
from typing import List, Callable

from nonebot.drivers import Driver
from nonebot import logger, get_driver
from nonebot.utils import run_sync, is_coroutine_callable

from migang.core import event_register

from .init_font import load_font
from .command_check import check_command
from .init_plugin_cd import init_plugin_cd
from .init_plugin_info import init_plugin_info
from .init_plugin_task import init_plugin_task
from .init_plugin_count import init_plugin_count
from .init_plugin_config import init_plugin_config

driver: Driver = get_driver()


async def run_cors(funcs: List[Callable], message: str):
    cors = [
        func() if is_coroutine_callable(func) else run_sync(func)() for func in funcs
    ]
    if cors:
        try:
            await asyncio.gather(*cors)
        except Exception as e:
            logger.error(f"执行{message}的函数出错：{e}")


@driver.on_startup
async def _():
    # 执行初始化前的函数
    await run_cors(event_register._pre_init_manager_func, "初始化前")
    await run_cors(event_register._pre_init_manager_func_l2, "初始化前l2")

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
    await run_cors(event_register._post_init_manager_func, "初始化后")
    await run_cors(event_register._post_init_manager_func_l2, "初始化后l2")


@driver.on_shutdown
async def _():
    run_cors(event_register._shutdown_func, "关闭前")
