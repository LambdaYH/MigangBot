from nonebot.log import logger

from migangbot.core.manager import plugin_manager, PluginType
from migangbot.core.permission import NORMAL

from .utils import get_plugin_list


async def init_plugin_info():
    plugins = get_plugin_list()
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
        plugin_type = (
            plugin.module.__getattribute__("__plugin_type__")
            if hasattr(plugin.module, "__plugin_type__")
            else PluginType.All
        )
        hidden = (
            plugin.module.__getattribute__("__plugin_hidden__")
            if hasattr(plugin.module, "__plugin_hidden__")
            else False
        )
        if not plugin_manager.check_plugin(plugin_name):
            await plugin_manager.add(
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
                hidden=hidden,
                permission=plugin.module.__getattribute__("__plugin_perm__")
                if hasattr(plugin.module, "__plugin_perm__")
                else NORMAL,
                plugin_type=plugin_type,
            )
            logger.info(f"已将插件 {plugin_name} 加入插件控制")
        else:
            plugin_manager.set_plugin_usage(plugin_name=plugin_name, usage=usage)
            plugin_manager.set_plugin_hidden(
                plugin_name=plugin_name,
                hidden=hidden,
            )
            plugin_manager.set_plugin_type(
                plugin_name=plugin_name, plugin_type=plugin_type
            )
    for i, e in enumerate(await plugin_manager.init()):
        if e:
            logger.error(f"无法将插件 {plugins[i].name} 加入插件控制：{e}")
        else:
            count += 1
    logger.info(f"已成功将 {count} 个插件加入插件控制")