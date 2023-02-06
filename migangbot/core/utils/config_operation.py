import sys
from typing import Optional, Any
from pathlib import Path

from migangbot.core.manager import config_manager


async def get_config(key: str, plugin_name: Optional[str] = None) -> Any:
    """异步获取插件配置，当plugin_name不指定且当前插件位于以plugins结尾的文件夹中时，插件名将默认为当前插件

    Args:
        key (str): 配置项键值
        plugin_name (Optional[str], optional): 插件名，当为空且当前插件位于以plugins结尾的文件夹中时，插件名将默认为当前插件，否则会发生未定义行为. Defaults to None.

    Returns:
        Any: 配置项值
    """
    if not plugin_name:
        file_path = Path(sys._getframe(1).f_code.co_filename)
        if str(file_path.parent).lower().endswith(("plugins", "plugin")):
            plugin_name = file_path.name.removesuffix(file_path.suffix)
        else:
            plugin_name = file_path.parent.name
    return await config_manager.async_get_config_item(
        plugin_name=plugin_name, plugin_config=key
    )


def sync_get_config(key: str, plugin_name: Optional[str] = None) -> Any:
    """同步获取插件配置，当plugin_name不指定且当前插件位于以plugins结尾的文件夹中时，插件名将默认为当前插件

    Args:
        key (str): 配置项键值
        plugin_name (Optional[str], optional): 插件名，当为空且当前插件位于以plugins结尾的文件夹中时，插件名将默认为当前插件，否则会发生未定义行为. Defaults to None.

    Returns:
        Any: 配置项值
    """
    if not plugin_name:
        file_path = Path(sys._getframe(1).f_code.co_filename)
        if str(file_path.parent).lower().endswith(("plugins", "plugin")):
            plugin_name = file_path.name.removesuffix(file_path.suffix)
        else:
            plugin_name = file_path.parent.name
    return config_manager.sync_get_config_item(
        plugin_name=plugin_name, plugin_config=key
    )
