import asyncio

from nonebot.log import logger

from migangbot.core.manager import count_manager

from .utils import GetPluginList


async def init_plugin_count():
    plugins = GetPluginList()
    count = 0
    add_ret = await asyncio.gather(
        *[
            count_manager.Add(
                plugin_name=plugin.name,
                count_items=plugin.module.__getattribute__("__plugin_count__"),
            )
            for plugin in plugins
            if hasattr(plugin.module, "__plugin_count__")
        ],
        return_exceptions=True,
    )
    for i, e in enumerate(add_ret):
        if e:
            logger.error(f"插件 {plugins[i].name} COUNT加载失败：{e}")
        else:
            count += 1
    if count != 0:
        logger.info(f"已成功将 {count} 个插件加入次数限制控制")
