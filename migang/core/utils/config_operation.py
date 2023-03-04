import sys
from pathlib import Path
from nonebot import get_loaded_plugins, get_driver
from typing import Any, Optional
from functools import cache

from migang.core.manager import config_manager

plugin_list = set()


@get_driver().on_startup
async def _():
    global plugin_list
    plugins = get_loaded_plugins()
    for plugin in plugins:
        plugin_list.add(plugin.name)


@cache
def get_module_by_filename(file: str):
    file_path = Path(file)
    if file_path.name == "__init__.py":
        return file_path.parent.name
    if file_path.parent.name in plugin_list:
        return file_path.parent.name
    elif (name := file_path.name.removesuffix(file_path.suffix)) in plugin_list:
        return name
    else:
        raise ValueError("无法自动获取插件名")


async def get_config(key: str, plugin_name: Optional[str] = None) -> Any:
    """异步获取插件配置，当plugin_name不指定时，插件名将默认为当前插件，最好不要在插件未完全加载时载入插件配置，否则第一次启动时会抛出异常且无法及时获取新默认值

    Args:
        key (str): 配置项键值
        plugin_name (Optional[str], optional): 插件名，当为空且当前插件位于以plugins结尾的文件夹中时，插件名将默认为当前插件，否则会发生未定义行为. Defaults to None.

    Returns:
        Any: 配置项值
    """
    if not plugin_name:
        plugin_name = get_module_by_filename(sys._getframe(1).f_code.co_filename)
    return await config_manager.async_get_config_item(
        plugin_name=plugin_name, plugin_config=key
    )


def sync_get_config(key: str, plugin_name: Optional[str] = None) -> Any:
    """同步获取插件配置，当plugin_name不指定时，插件名将默认为当前插件，最好不要在插件未完全加载时载入插件配置，否则第一次启动时会抛出异常且无法及时获取新默认值

    Args:
        key (str): 配置项键值
        plugin_name (Optional[str], optional): 插件名，当为空且当前插件位于以plugins结尾的文件夹中时，插件名将默认为当前插件，否则会发生未定义行为. Defaults to None.

    Returns:
        Any: 配置项值
    """
    if not plugin_name:
        plugin_name = get_module_by_filename(sys._getframe(1).f_code.co_filename)
    return config_manager.sync_get_config_item(
        plugin_name=plugin_name, plugin_config=key
    )
