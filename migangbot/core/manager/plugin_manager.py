import ujson as json
from pathlib import Path
from typing import Union, Dict, Set, List, Optional

from migangbot.core.permission import NORMAL
from migangbot.core.exception import FileTypeError
from migangbot.core.utils.file_operation import AsyncLoadData, AsyncSaveData


class Plugin:
    """
    管理单个插件或任务在群聊中的状态
    """

    def __init__(self, data: Dict, usage: Optional[str] = None) -> None:
        # 插件名
        self.__name = data["name"]
        self.__all_name: Set[str] = set(data["aliases"])
        self.__all_name.add(self.Name)
        self.__permission: int = data["permission"]
        self.__category: Optional[str] = data["category"]
        self.__author: str = data["author"]
        self.__version: str = data["version"]
        self.__Usage: Optional[str] = usage
        # 全局禁用状态
        self.__global_status: bool = data["global_status"]
        # 插件默认状态
        self.__default_status: bool = data["default_status"]
        # 快速查找用
        self.__non_default_group: Set[int] = (
            set(data["disbled_group"])
            if self.__default_status
            else set(data["enabled_group"])
        )
        # 保存入配置文件用，修改时需要2倍修改量
        self.__enabled_group: List[int] = data["enabled_group"]
        self.__disabled_group: List[int] = data["disbled_group"]

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
        self.__Usage = usage

    @property
    def Name(self) -> str:
        return self.__name

    @property
    def AllName(self) -> Set[str]:
        return self.__all_name

    @property
    def Usage(self) -> Optional[str]:
        return self.__Usage

    @property
    def Author(self) -> str:
        return self.__author

    @property
    def Version(self) -> str:
        return self.__version

    @property
    def Category(self) -> Optional[str]:
        return self.__category

    def CleanGroup(self, group_set: Set[int]):
        self.__non_default_group &= group_set
        if self.__default_status:
            self.__disabled_group.clear()
            self.__disabled_group += list(self.__non_default_group)
        else:
            self.__enabled_group.clear()
            self.__enabled_group += list(self.__non_default_group)


class PluginManager:
    """
    管理全部插件与任务

    插件名
    插件权限
    插件默认启用状态
    启用群组
    禁用群组
    """

    def __init__(self, file: Union[Path, str]) -> None:
        self.__data: Dict = {}  # 用于写入文件
        self.__plugin: Dict[str, Plugin] = {}  # 用于管理插件
        self.__plugin_aliases: Dict[str, str] = {}  # 建立插件别名与插件名的映射
        self.__file: Path = Path(file) if isinstance(file, str) else file

        if file.suffix != ".json":
            raise FileTypeError("插件管理模块配置文件必须为json格式！")

        file.parent.mkdir(parents=True, exist_ok=True)
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                self.__data = json.load(f)

        for plugin in self.__data:
            self.__plugin[plugin]: Plugin = Plugin(self.__data[plugin])
            for alias in self.__plugin[plugin].AllName:
                self.__plugin_aliases[alias] = plugin

    def CheckGroupStatus(
        self, plugin_name: str, group_id: int, group_permission: int
    ) -> bool:
        """
        检查插件是否响应
        若插件不受管理，则默认响应
        """
        return plugin_name not in self.__plugin or self.__plugin[
            plugin_name
        ].CheckGroupStatus(group_id=group_id, group_permission=group_permission)

    async def SetGroupEnable(
        self, plugin_name: str, group_id: int, auto_save=True
    ) -> bool:
        if plugin_name in self.__plugin and self.__plugin[plugin_name].SetGroupEnable(
            group_id
        ):
            if auto_save:
                await self.Save()
            return True
        return False

    async def SetGroupDisable(
        self, plugin_name: str, group_id: int, auto_save=True
    ) -> bool:
        if plugin_name in self.__plugin and self.__plugin[plugin_name].SetGroupDisable(
            group_id
        ):
            if auto_save:
                await self.Save()
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
        return self.__plugin[name].Usage

    def CheckPlugin(self, name: str) -> bool:
        """
        仅支持插件名
        """
        return name in self.__plugin

    def GetPluginList(self) -> Set[str]:
        return self.__data.keys()

    def GetPluginName(self, name: str) -> Optional[str]:
        return self.__plugin_aliases.get(name)

    async def ReLoad(self) -> None:
        self.__data = await AsyncLoadData(self.__file)
        self.__plugin.clear()
        for plugin in self.__data:
            self.__plugin[plugin]: Plugin = Plugin(self.__data[plugin])

    async def CleanGroup(self, group_list: Union[List[int], Set[int]]) -> None:
        group_list = set(group_list)
        for _, plugin in self.__plugin.items():
            plugin.CleanGroup(group_list)
        await self.Save()

    def SetPluginUsage(self, plugin_name: str, usage: Optional[str]):
        if plugin_name not in self.__plugin:
            return
        self.__plugin[plugin_name].SetUsage(usage=usage)

    async def Save(self):
        await AsyncSaveData(self.__data, self.__file)

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
        auto_save: bool = True,
    ) -> None:
        self.__data[plugin_name] = {
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
        }
        self.__plugin[plugin_name] = Plugin(data=self.__data[plugin_name], usage=usage)
        for alias in self.__plugin[plugin_name].AllName:
            self.__plugin_aliases[alias] = plugin_name
        if auto_save:
            await self.Save()

    async def Remove(self, plugin_name: str, auto_save: bool = True) -> None:
        if plugin_name in self.__data:
            del self.__data[plugin_name]
            del self.__plugin[plugin_name]
        if auto_save:
            await self.Save()
