from nonebot.log import logger

from migangbot.core.manager import plugin_manager
from migangbot.core.permission import NORMAL

from .utils import GetPluginList


async def init_plugin_info():
    plugins = GetPluginList()
    count = 0
    for plugin in plugins:
        plugin_name = plugin.name
        # 先填充metadata的数据再用属性
        try:
            name = (
                plugin.metadata.name
                if plugin.metadata and plugin.metadata.name
                else plugin.module.__getattribute__("__plugin_name__")
            )
        except AttributeError:
            logger.info(f"未将 {plugin_name} 加入插件控制")
            continue
        version, author, usage = None, None, None
        if metadata := plugin.metadata:
            version = metadata.extra.get("version")
            author = metadata.extra.get("author")
            usage = metadata.usage

        if not version:
            version = (
                plugin.module.__getattribute__("__plugin_version__")
                if hasattr(plugin.module, "__plugin_version__")
                else None
            )
        if not author:
            author = (
                plugin.module.__getattribute__("__plugin_author__")
                if hasattr(plugin.module, "__plugin_version__")
                else None
            )
        if not usage:
            usage = (
                plugin.module.__getattribute__("__plugin_usage__")
                if hasattr(plugin.module, "__plugin_version__")
                else None
            )
        if not plugin_manager.CheckPlugin(plugin_name):
            try:
                await plugin_manager.Add(
                    plugin_name=plugin_name,
                    name=name,
                    aliases=plugin.module.__getattribute__("__plugin_aliases__")
                    if hasattr(plugin.module, "__plugin_aliases__")
                    else [],
                    author=author,
                    version=version,
                    category=plugin.module.__getattribute__("__plugin_category__")
                    if hasattr(plugin.module, "__plugin_category__")
                    else "通用",
                    usage=usage,
                    default_status=plugin.module.__getattribute__("__default_status__")
                    if hasattr(plugin.module, "__default_status__")
                    else True,
                    permission=plugin.module.__getattribute__("__plugin_perm__")
                    if hasattr(plugin.module, "__plugin_perm__")
                    else NORMAL,
                    auto_save=False,
                )
                logger.info(f"已将插件 {plugin_name} 加入插件控制")
            except Exception as e:
                logger.error(f"无法将插件 {plugin_name} 加入插件控制：{e}")
                continue
        else:
            plugin_manager.SetPluginUsage(plugin_name=plugin_name, usage=usage)
        count += 1
    await plugin_manager.Save()
    logger.info(f"已成功将 {count} 个插件加入插件控制")
