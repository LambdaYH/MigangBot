from pathlib import Path

from .plugin_manager import PluginManager
from .group_manager import GroupManager
from .config_manager import ConfigManager, ConfigItem
from .cd_manager import CDManager, CDItem, CDCheckType, CDLimitType

core_data_path = Path() / "data" / "core"

plugin_manager: PluginManager = PluginManager(core_data_path / "plugin_manager.json")
task_manager: PluginManager = PluginManager(core_data_path / "task_manager.json")
group_manager: GroupManager = GroupManager(
    core_data_path / "group_manager.json",
    plugin_manager=plugin_manager,
    task_manager=task_manager,
)
config_manager: ConfigManager = ConfigManager()
cd_manager: CDManager = CDManager()
