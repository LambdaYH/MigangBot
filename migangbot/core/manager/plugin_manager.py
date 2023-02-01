import asyncio
from pathlib import Path
from typing import Union, Dict, Set, List, Optional, Any

from migangbot.core.permission import NORMAL
from migangbot.core.utils.file_operation import AsyncLoadData, AsyncSaveData

_file_path = Path() / "data" / "core" / "plugin_manager"
_file_path.mkdir(parents=True, exist_ok=True)


class PluginManager:
    """
    管理全部插件与任务

    插件名
    插件权限
    插件默认启用状态
    启用群组
    禁用群组
    """

    class Plugin:
        """
        管理单个插件或任务在群聊中的状态
        """

        def __init__(self, plugin_name: str, usage: Optional[str] = None) -> None:
            # 数据
            self.__data: Dict[str, Any]
            self.__file = _file_path / f"{plugin_name}.json"

            # 属性
            self.name: str
            self.all_name: Set[str]
            self.category: Optional[str]
            self.author: str
            self.version: str
            self.usage: Optional[str] = usage
            # 全局禁用状态
            self.__global_status: bool
            # 插件默认状态
            self.__default_status: bool
            # 快速查找用
            self.__non_default_group: Set[int]
            # 保存入配置文件用，修改时需要2倍修改量
            self.__enabled_group: List[int]
            self.__disabled_group: List[int]

        async def Init(self) -> None:
            self.__data = await AsyncLoadData(self.__file)
            self.name = self.__data["name"]
            self.all_name: Set[str] = set(self.__data["aliases"])
            self.all_name.add(self.name)
            self.__permission: int = self.__data["permission"]
            self.category: Optional[str] = self.__data["category"]
            self.author: str = self.__data["author"]
            self.version: str = self.__data["version"]
            self.__global_status: bool = self.__data["global_status"]
            self.__default_status: bool = self.__data["default_status"]
            self.__non_default_group: Set[int] = (
                set(self.__data["disbled_group"])
                if self.__default_status
                else set(self.__data["enabled_group"])
            )
            self.__enabled_group: List[int] = self.__data["enabled_group"]
            self.__disabled_group: List[int] = self.__data["disbled_group"]

        async def Save(self) -> None:
            await AsyncSaveData(self.__data, self.__file)

        def CheckGroupStatus(self, group_id: int, group_permission: int) -> bool:
            return (
                self.__global_status
                and (group_permission >= self.__permission)
                and (self.__default_status ^ (group_id in self.__non_default_group))
            )

        def SetGroupEnable(self, group_id: int) -> bool:
            if not self.__global_status:
                return False
            if self.__default_status:
                if group_id in self.__non_default_group:
                    self.__non_default_group.remove(group_id)
                    self.__disabled_group.remove(group_id)
                if group_id not in self.__enabled_group:
                    self.__enabled_group.append(group_id)
            else:
                if group_id not in self.__non_default_group:
                    self.__non_default_group.add(group_id)
                    self.__enabled_group.append(group_id)
                if group_id in self.__disabled_group:
                    self.__disabled_group.remove(group_id)
            return True

        def SetGroupDisable(self, group_id: int) -> bool:
            if self.__default_status:
                if group_id not in self.__non_default_group:
                    self.__non_default_group.add(group_id)
                    self.__disabled_group.append(group_id)
                if group_id in self.__enabled_group:
                    self.__enabled_group.remove(group_id)
            else:
                if group_id in self.__non_default_group:
                    self.__non_default_group.remove(group_id)
                    self.__enabled_group.remove(group_id)
                if group_id not in self.__disabled_group:
                    self.__disabled_group.append(group_id)
            return True

        def SetUsage(self, usage: Optional[str]) -> None:
            self.usage = usage

        def CleanGroup(self, group_set: Set[int]):
            self.__non_default_group &= group_set
            if self.__default_status:
                self.__disabled_group.clear()
                self.__disabled_group += list(self.__non_default_group)
            else:
                self.__enabled_group.clear()
                self.__enabled_group += list(self.__non_default_group)

    def __init__(self) -> None:
        self.__plugin: Dict[str, PluginManager.Plugin] = {}  # 用于管理插件
        self.__plugin_aliases: Dict[str, str] = {}  # 建立插件别名与插件名的映射
        plugin_files = _file_path.iterdir()
        for plugin_file in plugin_files:
            if plugin_file.suffix == ".json":
                plugin_name = plugin_file.name.removesuffix(".json")
                self.__plugin[plugin_name]: PluginManager.Plugin = PluginManager.Plugin(
                    plugin_name=plugin_name
                )

    async def Init(self):
        ret = await asyncio.gather(
            *[plugin.Init() for plugin in self.__plugin.values()],
            return_exceptions=True,
        )
        for i, plugin in enumerate(self.__plugin.values()):
            if not ret[i]:
                for alias in plugin.all_name:
                    self.__plugin_aliases[alias] = plugin.name
        return ret

    def CheckGroupStatus(
        self, plugin_name: str, group_id: int, group_permission: int
    ) -> bool:
        """
        检查插件是否响应
        若插件不受管理，则默认响应
        """
        return (
            not (plugin := self.__plugin.get(plugin_name))
        ) or plugin.CheckGroupStatus(
            group_id=group_id, group_permission=group_permission
        )

    async def SetGroupEnable(
        self, plugin_name: str, group_id: int, auto_save=True
    ) -> bool:
        if (plugin := self.__plugin.get(plugin_name)) and plugin.SetGroupEnable(
            group_id
        ):
            if auto_save:
                await plugin.Save()
            return True
        return False

    async def SetGroupDisable(
        self, plugin_name: str, group_id: int, auto_save=True
    ) -> bool:
        if (plugin := self.__plugin.get(plugin_name)) and plugin.SetGroupDisable(
            group_id
        ):
            if auto_save:
                await plugin.Save()
            return True
        return False

    def GetPluginUsage(self, name: str) -> Optional[str]:
        """
        获取插件帮助，支持模块名与别名
        """
        if name not in self.__plugin and name not in self.__plugin_aliases:
            return None
        if name not in self.__plugin:
            name = self.__plugin_aliases[name]
        return self.__plugin[name].usage

    def CheckPlugin(self, name: str) -> bool:
        """
        仅支持插件名
        """
        return name in self.__plugin

    def GetPluginList(self) -> Set[str]:
        return self.__plugin.keys()

    def GetPluginName(self, name: str) -> Optional[str]:
        return self.__plugin_aliases.get(name)

    async def CleanGroup(self, group_list: Union[List[int], Set[int]]) -> None:
        group_list = set(group_list)
        for plugin in self.__plugin.values():
            plugin.CleanGroup(group_list)
        await asyncio.gather(*[plugin.Save() for plugin in self.__plugin.values()])

    def SetPluginUsage(self, plugin_name: str, usage: Optional[str]):
        if plugin_name not in self.__plugin:
            return
        self.__plugin[plugin_name].SetUsage(usage=usage)

    async def Add(
        self,
        plugin_name: str,
        name: str,
        aliases: List[str] = [],
        author: Optional[str] = None,
        version: Union[str, int, None] = None,
        category: Optional[str] = None,
        usage: Optional[str] = None,
        default_status: bool = True,
        permission: int = NORMAL,
    ) -> None:
        await AsyncSaveData(
            {
                "name": name,
                "aliases": aliases,
                "permission": permission,
                "global_status": True,
                "default_status": default_status,
                "enabled_group": [],
                "disbled_group": [],
                "category": category,
                "author": author,
                "version": version,
            },
            _file_path / f"{plugin_name}.json",
        )
        self.__plugin[plugin_name] = PluginManager.Plugin(
            plugin_name=plugin_name, usage=usage
        )

    async def Remove(self, plugin_name: set) -> None:
        if plugin_name in self.__plugin:
            del self.__plugin[plugin_name]
            (_file_path / f"{plugin_name}.json").unlink()
