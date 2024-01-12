import sys
from pathlib import Path
from functools import cache
from typing import Any, Callable, Optional

from nonebot.log import logger
from nonebot import get_loaded_plugins

from migang.core.manager import config_manager
from migang.core.exception import ConfigNoExistError
from migang.core.event_register import pre_init_manager

plugin_list = set()


@pre_init_manager
async def load_plugin_list():
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


def sync_get_config(
    key: str, plugin_name: Optional[str] = None, default_value=None
) -> Any:
    """同步获取插件配置，当plugin_name不指定时，插件名将默认为当前插件，最好不要在插件未完全加载时载入插件配置，否则第一次启动时会抛出异常且无法及时获取新默认值

    Args:
        key (str): 配置项键值
        plugin_name (Optional[str], optional): 插件名，当为空且当前插件位于以plugins结尾的文件夹中时，插件名将默认为当前插件，否则会发生未定义行为. Defaults to None.
        default_value: 因为一般在全局里面才用这种方式获取配置文件，而首次加载时配置项不存在会引发异常，所以当首次加载时使用这个default_value

    Returns:
        Any: 配置项值
    """
    if not plugin_name:
        plugin_name = get_module_by_filename(sys._getframe(1).f_code.co_filename)
    try:
        return config_manager.sync_get_config_item(
            plugin_name=plugin_name, plugin_config=key
        )
    except ConfigNoExistError:
        logger.info(f"{plugin_name} 的参数项 {key} 不存在，加载默认值 {default_value}")
        return default_value
