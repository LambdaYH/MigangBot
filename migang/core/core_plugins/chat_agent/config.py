from __future__ import annotations

from typing import Any

from migang.core.manager import config_manager
from migang.core.exception import ConfigNoExistError

PRIMARY_PLUGIN = "chat_agent"
LEGACY_PLUGIN = "chat_chatgpt"


def _is_empty_config_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (str, list, tuple, dict, set)):
        return len(value) == 0
    return False


async def get_agent_config(key: str, default_value: Any = None) -> Any:
    try:
        value = await config_manager.async_get_config_item(PRIMARY_PLUGIN, key)
    except ConfigNoExistError:
        value = None

    if not _is_empty_config_value(value):
        return value

    try:
        legacy_value = await config_manager.async_get_config_item(LEGACY_PLUGIN, key)
    except ConfigNoExistError:
        legacy_value = None

    if not _is_empty_config_value(legacy_value):
        return legacy_value
    return default_value


def sync_get_agent_config(key: str, default_value: Any = None) -> Any:
    try:
        value = config_manager.sync_get_config_item(PRIMARY_PLUGIN, key)
    except ConfigNoExistError:
        value = None

    if not _is_empty_config_value(value):
        return value

    try:
        legacy_value = config_manager.sync_get_config_item(LEGACY_PLUGIN, key)
    except ConfigNoExistError:
        legacy_value = None

    if not _is_empty_config_value(legacy_value):
        return legacy_value
    return default_value
