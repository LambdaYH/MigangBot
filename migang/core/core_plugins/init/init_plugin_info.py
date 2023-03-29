import asyncio
from typing import Any, Dict, Iterable, Optional

import aiohttp
from nonebot.log import logger

from migang.core.permission import NORMAL
from migang.core.manager.plugin_manager import CUSTOM_USAGE_FILE
from migang.core.manager import PluginType, core_data_path, plugin_manager
from migang.core.utils.file_operation import async_load_data, async_save_data

from .utils import get_plugin_list


async def _get_store_plugin_list() -> Dict[str, Dict[str, Any]]:
    try:
        async with aiohttp.ClientSession() as client:
            r = await (
                await client.get(
                    "https://ghproxy.com/https://raw.githubusercontent.com/nonebot/nonebot2/master/website/static/plugins.json",
                    timeout=30,
                )
            ).json(content_type=None)
    except asyncio.TimeoutError:
        logger.warning(f"连接Nonebot2商店超时，无法加载商店插件信息")
        return {}
    ret = {}
    for plugin in r:
        ret[plugin["module_name"]] = plugin
    return ret


async def init_plugin_info():
    plugins = get_plugin_list()
    count = 0
    store_plugin_list: Optional[Dict] = None
    plugin_file_list = set(
        [file.name for file in (core_data_path / "plugin_manager").iterdir()]
    )
    custom_usage = await async_load_data(CUSTOM_USAGE_FILE)

    for plugin in plugins:
        plugin_name = plugin.name
        version, author, usage = None, None, None
        # 先填充metadata的数据再用属性
        try:
            name = (
                plugin.metadata.name
                if plugin.metadata and plugin.metadata.name
                else plugin.module.__getattribute__("__plugin_name__")
            )
        except AttributeError:
            # logger.info(f"未将 {plugin_name} 加入插件控制")
            name = plugin_name
            if f"{plugin_name}.json" not in plugin_file_list:
                if store_plugin_list is None:
                    store_plugin_list = await _get_store_plugin_list()
                # 从商店加载
                if plugin_name in store_plugin_list:
                    p = store_plugin_list[plugin_name]
                    name = p["name"]
                    usage = p["desc"]
                    author = p["author"]
                    custom_usage[plugin_name] = usage
                    try:
                        async with aiohttp.ClientSession() as client:
                            async with await client.get(
                                f"https://pypi.org/pypi/{p['project_link']}/json",
                                timeout=10,
                            ) as r:
                                r = await r.json()
                                version = r["info"]["version"]
                    except Exception as e:
                        logger.warning(f"从pypi读取 {plugin_name} 版本信息失败：{e}")
                else:
                    logger.warning(
                        f"无法读取插件 {plugin_name} 信息，请检查插件信息是否正确定义或修改data/core/plugin_manager/{plugin_name}.json后重新启动"
                    )
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
        if plugin_name in custom_usage:
            usage = custom_usage[plugin_name]

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
        always_on = (
            plugin.module.__getattribute__("__plugin_always_on__")
            if hasattr(plugin.module, "__plugin_always_on__")
            else False
        )
        group_permission = user_permission = NORMAL
        if hasattr(plugin.module, "__plugin_perm__"):
            perm = plugin.module.__getattribute__("__plugin_perm__")
            if isinstance(perm, Iterable):
                if len(perm) >= 2:
                    group_permission = perm[0]
                    user_permission = perm[1]
                elif len(perm) == 1:
                    group_permission = perm[0]
            else:
                group_permission = perm

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
            else "功能",
            usage=usage,
            default_status=plugin.module.__getattribute__("__default_status__")
            if hasattr(plugin.module, "__default_status__")
            else True,
            hidden=hidden,
            group_permission=group_permission,
            user_permission=user_permission,
            always_on=always_on,
            plugin_type=plugin_type,
        ):
            logger.info(f"已将插件 {plugin_name} 加入插件控制")

    for i, e in enumerate(await plugin_manager.init()):
        if e:
            logger.error(f"无法将插件 {plugins[i].name} 加入插件控制：{e}")
        else:
            count += 1
    await async_save_data(custom_usage, CUSTOM_USAGE_FILE)
    logger.info(f"已成功将 {count} 个插件加入插件控制")
