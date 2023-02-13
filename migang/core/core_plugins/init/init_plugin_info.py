from nonebot.log import logger

from migang.core.manager import plugin_manager, PluginType, core_data_path
from migang.core.permission import NORMAL

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
            # logger.info(f"未将 {plugin_name} 加入插件控制")
            if not (core_data_path / "plugin_manager" / f"{plugin_name}.json").exists():
                logger.warning(
                    f"无法读取插件 {plugin_name} 信息，请检查插件信息是否正确定义或修改data/core/plugin_manager/{plugin_name}.json后重新启动"
                )
            name = plugin_name
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
        if await plugin_manager.add(
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
        ):
            logger.info(f"已将插件 {plugin_name} 加入插件控制")
    for i, e in enumerate(await plugin_manager.init()):
        if e:
            logger.error(f"无法将插件 {plugins[i].name} 加入插件控制：{e}")
        else:
            count += 1
    logger.info(f"已成功将 {count} 个插件加入插件控制")
