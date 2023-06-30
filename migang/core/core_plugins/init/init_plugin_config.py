import asyncio
from pathlib import Path
from collections import defaultdict
from typing import Any, List, Iterable, DefaultDict

import anyio
import ujson as json
from nonebot import get_driver
from nonebot.log import logger
from pydantic import BaseModel
from dotenv import dotenv_values

from migang.core.manager import ConfigItem, config_manager

from .utils import get_plugin_list


def _parse_basemodel_config(config: BaseModel):
    config = config.__dict__["__fields__"]
    config_items: List[ConfigItem] = []
    for v in config.values():
        config_items.append(
            ConfigItem(
                key=v.name, initial_value=v.default, default_value=v.default, env=True
            )
        )
    return config_items


def _parse_value(value: Any) -> str:
    if isinstance(value, dict) or isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


async def init_plugin_config():
    plugins = get_plugin_list()
    tasks = []
    all_configs: DefaultDict[str, List[ConfigItem]] = defaultdict(lambda: [])
    for plugin in plugins:
        if (not hasattr(plugin.module, "__plugin_config__")) and (
            not plugin.metadata or not plugin.metadata.config
        ):
            continue
        configs: List[ConfigItem] = []
        # 兼容metadata的config
        # if plugin.metadata and (c := plugin.metadata.config):
        #     if c.__base__ is BaseModel:
        #         configs += _parse_basemodel_config(c)
        if hasattr(plugin.module, "__plugin_config__"):
            c = plugin.module.__getattribute__("__plugin_config__")
            if isinstance(c, Iterable):
                configs += c
            elif isinstance(c, ConfigItem):
                configs.append(c)
        try:
            tasks.append(
                config_manager.add_configs(plugin_name=plugin.name, configs=configs)
            )
            for config in configs:
                all_configs[
                    config.config_name if config.config_name else plugin.name
                ].append(config)
        except Exception as e:
            logger.error(f"插件 {plugin.name} 配置加载失败：{e}")
    for i, e in enumerate(await asyncio.gather(*tasks, return_exceptions=True)):
        if e:
            logger.error(f"插件 {plugins[i].name} 配置加载失败：{e}")
    # 自动管理metadata的配置项，自动管理.env中的配置，以configs文件夹中配置为主，若不同，则更新.env文件
    # 代价就是有改动后必须要重启，以及会把.env弄乱掉
    env_file = Path() / f".env.{get_driver().env}"
    env_values = dotenv_values(env_file)
    modified = False

    # 会让缓存提前热身......
    async def check_env_config(plugin_name: str, config: ConfigItem):
        nonlocal modified, env_values
        # 检测配置项更新
        value = await config_manager.async_get_config_item(
            plugin_name=plugin_name, plugin_config=config.key
        )
        if (
            config.key not in env_values
            and _parse_value(value) != _parse_value(config.default_value)
        ) or (
            config.key in env_values and _parse_value(value) != env_values[config.key]
        ):
            env_values[config.key] = _parse_value(value)
            modified = True

        # 去除和默认值一样的配置项
        if config.key in env_values and env_values[config.key] == _parse_value(
            config.default_value
        ):
            del env_values[config.key]
            modified = True

    tasks = []
    for k, v in all_configs.items():
        tasks += [
            check_env_config(plugin_name=k, config=config) for config in v if config.env
        ]
    await asyncio.gather(*tasks)
    env_str = "\n".join(f"{k} = {v}" for k, v in env_values.items())
    async with await anyio.open_file(env_file, "w") as f:
        await f.write(env_str)
    if modified:
        logger.warning("检测到env文件中变量已更新，建议重新启动Bot以使得插件能获取到最新的配置文件")
    # 保存最新的默认值进文件
    await config_manager.save_default_value()
