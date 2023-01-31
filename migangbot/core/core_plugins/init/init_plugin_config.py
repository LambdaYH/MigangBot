from nonebot.log import logger
from nonebot.plugin import get_loaded_plugins

from migangbot.core.manager import config_manager, ConfigItem
from migangbot.core.permission import NORMAL

from .utils import GetPluginList


async def init_plugin_config():
    plugins = GetPluginList()
    for plugin in plugins:
        if not hasattr(plugin.module, "__plugin_config__"):
            continue
        configs = plugin.module.__getattribute__("__plugin_config__")
        if type(configs) is ConfigItem:
            await config_manager.AddConfig(plugin_name=plugin.name, config=configs)
        elif type(configs) is list:
            await config_manager.AddConfigs(plugin_name=plugin.name, configs=configs)
