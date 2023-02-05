from nonebot.log import logger

from migangbot.core.manager import cd_manager

from .utils import get_plugin_list


def init_plugin_cd():
    plugins = get_plugin_list()
    count = 0
    for plugin in plugins:
        if hasattr(plugin.module, "__plugin_cd__"):
            try:
                cd_manager.add(
                    plugin_name=plugin.name,
                    cd_items=plugin.module.__getattribute__("__plugin_cd__"),
                )
                count += 1
            except Exception as e:
                logger.error(f"插件 {plugin.name} CD加载失败：{e}")
    if count != 0:
        logger.info(f"已成功将 {count} 个插件加入CD控制")
