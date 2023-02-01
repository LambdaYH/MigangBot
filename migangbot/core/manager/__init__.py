from pathlib import Path

from .plugin_manager import PluginManager
from .group_manager import GroupManager
from .config_manager import ConfigManager, ConfigItem
from .cd_manager import CDManager, CDItem
from .count_manager import CountManager, CountPeriod, CountItem

from .data_type import LimitType, CheckType, CountPeriod

core_data_path = Path() / "data" / "core"

plugin_manager: PluginManager = PluginManager()
task_manager: PluginManager = PluginManager()
group_manager: GroupManager = GroupManager(
    core_data_path / "group_manager.json",
    plugin_manager=plugin_manager,
    task_manager=task_manager,
)
config_manager: ConfigManager = ConfigManager()
cd_manager: CDManager = CDManager()
count_manager: CountManager = CountManager()
