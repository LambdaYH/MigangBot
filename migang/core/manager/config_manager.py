from pathlib import Path
from typing import Dict, Any, Optional, List

from ruamel.yaml import CommentedMap
from async_lru import alru_cache
from cachetools import cached, LRUCache

from migang.core.utils.file_operation import (
    async_load_data,
    async_save_data,
    load_data,
)
from migang.core.exception import ConfigNoExistError
from migang.core.path import DATA_PATH

_config_path = Path() / "configs"
_config_path.mkdir(parents=True, exist_ok=True)


class ConfigItem:
    """__plugin_config__属性为List[ConfigItem]或ConfigItem"""

    def __init__(
        self,
        key: str,
        initial_value: Optional[Any] = None,
        default_value: Optional[Any] = None,
        description: Optional[str] = None,
        config_name: Optional[str] = None,
        env: bool = False,
    ) -> None:
        """ConfigItem构造函数

        Args:
            key (str): 配置项键值
            initial_value (Optional[Any], optional): 配置项初始值，生成配置文件时应用该值. Defaults to None.
            default_value (Optional[Any], optional): 配置项默认值，当键值对应配置值为空时，应用该值. Defaults to None.
            description (Optional[str], optional): 配置项说明，在配置文件中以注释的形式存在. Defaults to None.
            config_name (Optional[str], optional): 配置项所在配置文件名，为空时则默认使用插件名. Defaults to None.
            env (bool, optional): 是否将配置项写入.env文件，主要用于兼容nonebot的metadata. Defaults to False.
        """
        self.key = key
        self.initial_value = initial_value
        self.default_value = default_value
        self.description = description
        self.config_name = config_name
        self.env = env


class ConfigManager:
    """
    管理插件的配置
    """

    def __init__(self) -> None:
        """仅初始化配置项默认值，当所需配置值时从文件加载并加入缓存"""
        self.__default_value: Dict[str, Dict[str, Any]] = load_data(
            DATA_PATH / "core" / "default_value_cache.json"
        )
        """{plugin_name: {"key": value}}
        """

    async def save_default_value(self):
        await async_save_data(
            self.__default_value, DATA_PATH / "core" / "default_value_cache.json"
        )

    async def add_config(self, plugin_name: str, config: ConfigItem) -> None:
        """添加单个配置项

        Args:
            plugin_name (str): 插件名或配置文件名
            config (ConfigItem): 配置项
        """
        if config.config_name:
            plugin_name = config.config_name
        file_name = _config_path / f"{plugin_name}.yaml"
        data: CommentedMap = await async_load_data(file_name)
        if plugin_name not in self.__default_value:
            self.__default_value[plugin_name] = {}
        self.__default_value[plugin_name][config.key] = config.default_value
        if config.key in data:
            return
        data[config.key] = config.initial_value
        data.yaml_set_comment_before_after_key(
            key=config.key, before=config.description
        )
        await async_save_data(data, file_name)

    async def add_configs(self, plugin_name: str, configs: List[ConfigItem]) -> None:
        """添加多个配置项

        Args:
            plugin_name (str): 插件名或配置文件名
            configs (List[ConfigItem]): 配置项
        """
        if plugin_name not in self.__default_value:
            self.__default_value[plugin_name] = {}
        file_name = _config_path / f"{plugin_name}.yaml"
        data: CommentedMap = await async_load_data(file_name)
        for config in configs:
            if config.config_name:
                await self.add_config(plugin_name, config)
                continue
            self.__default_value[plugin_name][config.key] = config.default_value
            if config.key in data:
                continue
            data[config.key] = config.initial_value
            data.yaml_set_comment_before_after_key(
                key=config.key, before=config.description
            )
        await async_save_data(data, file_name)

    @alru_cache(maxsize=128)
    async def __async_get_config(self, plugin_name: str) -> CommentedMap:
        """读取插件名对应的配置名
        Args:
            plugin_name (str): 插件名或配置文件名

        Returns:
            CommentedMap: 配置，类Dict结构
        """
        return await async_load_data(_config_path / f"{plugin_name}.yaml")

    @alru_cache(maxsize=256)
    async def async_get_config_item(self, plugin_name: str, plugin_config: str) -> Any:
        """获取plugin_name对应的键值为plugin_config的配置值

        Args:
            plugin_name (str): 插件名或配置文件名
            plugin_config (str): 配置项键值

        Raises:
            ConfigNoExistError: 若不存在plugin_name中plugin_config对应的配置文件，则抛出异常

        Returns:
            Any: 配置值
        """
        data = await self.__async_get_config(plugin_name)
        if plugin_config not in data:
            raise ConfigNoExistError(f"插件 {plugin_name} 的配置项 {plugin_config} 不存在！")
        return (
            data[plugin_config]
            if data[plugin_config] is not None
            else (
                self.__default_value[plugin_name].get(plugin_config)
                if plugin_name in self.__default_value
                else None
            )
        )

    @cached(cache=LRUCache(maxsize=128))
    def __sync_get_config(self, plugin_name: str) -> CommentedMap:
        return load_data(_config_path / f"{plugin_name}.yaml")

    @cached(cache=LRUCache(maxsize=256))
    def sync_get_config_item(self, plugin_name: str, plugin_config: str) -> Any:
        """获取plugin_name对应的键值为plugin_config的配置值

        Args:
            plugin_name (str): 插件名或配置文件名
            plugin_config (str): 配置项键值

        Raises:
            ConfigNoExistError: 若不存在plugin_name中plugin_config对应的配置文件，则抛出异常

        Returns:
            Any: 配置值
        """
        data = self.__sync_get_config(plugin_name)
        if plugin_config not in data:
            raise ConfigNoExistError(f"插件 {plugin_name} 的配置项 {plugin_config} 不存在！")
        return (
            data[plugin_config]
            if data[plugin_config] is not None
            else (
                self.__default_value[plugin_name].get(plugin_config)
                if plugin_name in self.__default_value
                else None
            )
        )
