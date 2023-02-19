from pathlib import Path

from nonebot.log import logger
from nonebot import get_driver

from .plugin_manager import PluginManager
from .task_manager import TaskManager, TaskItem
from .group_manager import GroupManager
from .user_manager import UserManager
from .config_manager import ConfigManager, ConfigItem
from .cd_manager import CDManager, CDItem
from .count_manager import CountManager, CountPeriod, CountItem
from .request_manager import RequestManager
from .permission_manager import PermissionManager

from .data_class import LimitType, CheckType, CountPeriod, PluginType

core_data_path = Path() / "data" / "core"
config_path = Path() / "configs"

plugin_manager: PluginManager = PluginManager(core_data_path / "plugin_manager")
"""插件运行前检查，控制整个插件的状态，实现整个插件的启闭
"""

task_manager: TaskManager = TaskManager(core_data_path / "task_manager")
"""更小粒度的控制，能够在matcher中使用rule检测或直接在业务代码中检测
"""

group_manager: GroupManager = GroupManager(
    core_data_path / "group_manager.json",
    plugin_manager=plugin_manager,
    task_manager=task_manager,
)
"""对群权限以及群机器人启闭情况进行控制，此对象内嵌plugin_manager与task_manager，用于管理群内插件与任务的状态
"""

user_manager: UserManager = UserManager(
    core_data_path / "user_manager.json",
    plugin_manager=plugin_manager,
)
"""管理用户权限，仅在私聊状态下生效
"""

config_manager: ConfigManager = ConfigManager(config_path)
"""读取插件的__plugin_config__属性并自动生成对应配置文件，同时可用于获取添加进入的配置项，__plugin_config__属性为List[ConfigItem]或ConfigItem
"""

cd_manager: CDManager = CDManager()
"""读取插件的__plugin_cd__属性用于限制插件cd，__plugin_cd__属性为List[CDItem]或CDItem
"""

count_manager: CountManager = CountManager(core_data_path / "count_manager")
"""读取插件__plugin_count__属性用于限制插件在一定周期内调用次数，__plugin_count__属性为List[CountItem]或CountItem
"""

request_manager: RequestManager = RequestManager(
    core_data_path / "request_manager.json"
)
"""管理各种请求
"""

permission_manager: PermissionManager = PermissionManager(
    core_data_path / "permission_manager.json"
)
"""管理权限，设置限时权限
"""

async def save():
    """保存各管理器需要保存的文件"""
    import asyncio

    logger.debug("正在持久化数据...")
    await asyncio.gather(
        *[
            group_manager.save(),
            user_manager.save(),
            count_manager.save(),
            permission_manager.save(),
        ]
    )
    logger.debug("数据持久化完成...")
