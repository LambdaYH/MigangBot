import asyncio

from nonebot.log import logger
from nonebot.plugin import get_loaded_plugins

from migangbot.core.manager import config_manager, ConfigItem
from migangbot.core.permission import NORMAL

from .utils import get_plugin_list


async def init_plugin_config():
    plugins = get_plugin_list()
    tasks = []
    for plugin in plugins:
        if not hasattr(plugin.module, "__plugin_config__"):
            continue
        configs = plugin.module.__getattribute__("__plugin_config__")
        try:
            if type(configs) is ConfigItem:
                tasks.append(
                    config_manager.add_config(plugin_name=plugin.name, config=configs)
                )
            elif type(configs) is list:
                tasks.append(
                    config_manager.add_configs(plugin_name=plugin.name, configs=configs)
                )
        except Exception as e:
            logger.error(f"插件 {plugin.name} 配置加载失败：{e}")
    for i, e in enumerate(await asyncio.gather(*tasks, return_exceptions=True)):
        if e:
            logger.error(f"插件 {plugins[i].name} 配置加载失败：{e}")
