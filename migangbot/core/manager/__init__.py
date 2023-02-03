from pathlib import Path

from .plugin_manager import PluginManager
from .task_manager import TaskManager, TaskItem
from .group_manager import GroupManager
from .user_manager import UserManager
from .config_manager import ConfigManager, ConfigItem
from .cd_manager import CDManager, CDItem
from .count_manager import CountManager, CountPeriod, CountItem

from .data_class import LimitType, CheckType, CountPeriod, PluginType

core_data_path = Path() / "data" / "core"

# plugin_manager是运行前检查
plugin_manager: PluginManager = PluginManager(core_data_path / "plugin_manager")
# task_manager是推送前检查，更精确控制消息发送
task_manager: TaskManager = TaskManager(core_data_path / "task_manager")
group_manager: GroupManager = GroupManager(
    core_data_path / "group_manager.json",
    plugin_manager=plugin_manager,
    task_manager=task_manager,
)
user_manager: UserManager = UserManager(
    core_data_path / "user_manager.json",
    plugin_manager=plugin_manager,
)
config_manager: ConfigManager = ConfigManager()
cd_manager: CDManager = CDManager()
count_manager: CountManager = CountManager()


async def Save():
    import asyncio

    await asyncio.gather(
        *[group_manager.Save(), user_manager.Save(), count_manager.Save()]
    )
