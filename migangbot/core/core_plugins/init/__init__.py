import asyncio
from nonebot import Driver, get_driver

from .init_plugin_info import init_plugin_info
from .init_plugin_config import init_plugin_config
from .init_plugin_cd import init_plugin_cd

_driver: Driver = get_driver()


@_driver.on_startup
async def _():
    await asyncio.gather(*[init_plugin_info(), init_plugin_config()])
    init_plugin_cd()
