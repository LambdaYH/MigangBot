from pathlib import Path
from typing import Dict, Any, Optional, List

from ruamel.yaml import CommentedMap
from async_lru import alru_cache

from migangbot.core.utils.file_operation import AsyncLoadData, AsyncSaveData
from migangbot.core.exception import ConfigNoExistError

_config_path = Path() / "configs"
_config_path.mkdir(parents=True, exist_ok=True)


class ConfigItem:
    def __init__(
        self,
        key: str,
        initial_value: Optional[Any] = None,
        default_value: Optional[Any] = None,
        description: Optional[str] = None,
        config_name: Optional[str] = None,
    ) -> None:
        self.key = key
        self.initial_value = initial_value
        self.default_value = default_value
        self.description = description
        self.config_name = config_name


class ConfigManager:
    def __init__(self) -> None:
        self.__default_value: Dict[str, Dict[str, Any]] = {}

    async def AddConfig(self, plugin_name: str, config: ConfigItem) -> None:
        if config.config_name:
            plugin_name = config.config_name
        file_name = _config_path / f"{plugin_name}.yaml"
        data: CommentedMap = await AsyncLoadData(file_name)
        if plugin_name not in self.__default_value:
            self.__default_value[plugin_name] = {}
        self.__default_value[plugin_name][config.key] = config.default_value
        if config.key in data:
            return
        data[config.key] = config.initial_value
        data.yaml_set_comment_before_after_key(
            key=config.key, before=config.description
        )
        await AsyncSaveData(data, file_name)

    async def AddConfigs(self, plugin_name: str, configs: List[ConfigItem]) -> None:
        if plugin_name not in self.__default_value:
            self.__default_value[plugin_name] = {}
        file_name = _config_path / f"{plugin_name}.yaml"
        data: CommentedMap = await AsyncLoadData(file_name)
        for config in configs:
            if config.config_name:
                await self.AddConfig(plugin_name, config)
                continue
            self.__default_value[plugin_name][config.key] = config.default_value
            if config.key in data:
                continue
            data[config.key] = config.initial_value
            data.yaml_set_comment_before_after_key(
                key=config.key, before=config.description
            )
        await AsyncSaveData(data, file_name)

    @alru_cache(maxsize=128)
    async def __GetConfig(self, plugin_name: str):
        data: CommentedMap = await AsyncLoadData(_config_path / f"{plugin_name}.yaml")
        return data

    @alru_cache(maxsize=256)
    async def GetConfigItem(self, plugin_name: str, plugin_config: str):
        data = await self.__GetConfig(plugin_name)
        if plugin_config not in data:
            raise ConfigNoExistError(f"插件 {plugin_name} 的配置项 {plugin_config} 不存在！")
        return (
            data[plugin_config]
            if data[plugin_config]
            else self.__default_value[plugin_name][plugin_config]
        )
