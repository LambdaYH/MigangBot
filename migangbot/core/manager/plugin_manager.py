import asyncio
from pathlib import Path
from typing import Union, Dict, Set, List, Optional, Any

import aiofiles
from pydantic import BaseModel

from migangbot.core.manager.data_class import PluginType
from migangbot.core.permission import NORMAL


class PluginManager:
    """管理全部插件"""

    class PluginAttr(BaseModel):
        name: str
        aliases: Set[str]
        permission: int
        global_status: bool
        default_status: bool
        enabled_group: Set[int]
        disabled_group: Set[int]
        category: str
        author: str
        version: str

    class Plugin:
        """
        管理单个插件
        """

        def __init__(
            self,
            file,
            usage: Optional[str] = None,
            hidden: bool = False,
            plugin_type: PluginType = PluginType.All,
        ) -> None:
            """Plugin构造函数

            Args:
                file (_type_): 插件所对应的配置文件名
                usage (Optional[str], optional): 插件用法. Defaults to None.
                hidden (bool, optional): 插件是否隐藏. Defaults to False.
                plugin_type (PluginType, optional): 插件类型. Defaults to PluginType.All.
            """
            # 数据
            self.__data: PluginManager.PluginAttr
            self.__file = file

            # 属性
            self.plugin_name = self.__file.name.removesuffix(".json")
            self.name: str
            """自己的命名，为metadata中的name或__plugin_name__
            """
            self.plugin_type: PluginType = plugin_type  # 只是一种提示，用于生成帮助界面
            self.all_name: Set[str]
            """包括name与别名在内的所有名字
            """
            self.category: Optional[str]
            """插件类别，生成帮助用
            """
            self.author: str
            self.version: str
            self.usage: Optional[str] = usage
            self.hidden: bool = hidden
            self.__permission: int
            self.__global_status: bool
            """插件全局状态
            """
            self.__default_status: bool
            """插件默认状态
            """
            self.__non_default_group: Set[int]
            """用于快速查找
            """

        async def init(self) -> None:
            """异步初始化插件"""
            async with aiofiles.open(self.__file, "r") as f:
                self.__data = PluginManager.PluginAttr.parse_raw(await f.read())
            self.name = self.__data.name
            self.all_name: Set[str] = self.__data.aliases
            self.all_name.add(self.name)
            self.__permission: int = self.__data.permission
            self.category: Optional[str] = self.__data.category
            self.author: str = self.__data.author
            self.version: str = self.__data.version
            self.__global_status: bool = self.__data.global_status
            self.__default_status: bool = self.__data.default_status
            self.__non_default_group: Set[int] = (
                self.__data.disabled_group
                if self.__default_status
                else self.__data.enabled_group
            )

        async def save(self) -> None:
            """将插件数据存储到硬盘"""
            async with aiofiles.open(self.__file, "w") as f:
                await f.write(self.__data.json(ensure_ascii=False, indent=4))

        def set_plugin_type(self, type: PluginType):
            """设置插件类型

            Args:
                type (PluginType): 插件类型
            """
            self.plugin_type = type

        @property
        def global_status(self) -> bool:
            """插件全局状态

            Returns:
                bool: 插件全局状态
            """
            return self.__global_status

        def enable(self) -> None:
            """全局启用"""
            self.__data.global_status = self.__global_status = True

        def disable(self) -> None:
            """全局禁用"""
            self.__data.global_status = self.__global_status = False

        def check_group_status(self, group_id: int, group_permission: int) -> bool:
            """检测群是否能调用该插件

            Args:
                group_id (int): 群号
                group_permission (int): 群权限

            Returns:
                bool: 若能调用，返回True
            """
            return (
                self.__global_status
                and (group_permission >= self.__permission)
                and (self.__default_status ^ (group_id in self.__non_default_group))
            )

        def check_user_status(self, user_permission: int) -> bool:
            """检测用户是否能调用该插件

            Args:
                user_permission (int): 用户权限

            Returns:
                bool: 若能调用，返回True
            """
            return self.__global_status and user_permission >= self.__permission

        def check_permission(self, permission: int) -> bool:
            """检测权限

            Args:
                permission (int): 权限

            Returns:
                bool: 若权限足够，返回True
            """
            return permission >= self.__permission

        def set_group_enable(self, group_id: int) -> bool:
            """在群group_id中启用该插件

            Args:
                group_id (int): 群号

            Returns:
                bool: 若全局禁用则无法启用返回False，反之返回True
            """
            if not self.__global_status:
                return False
            if self.__default_status:
                if group_id in self.__non_default_group:
                    self.__non_default_group.remove(group_id)
                if group_id not in self.__data.enabled_group:
                    self.__data.enabled_group.add(group_id)
            else:
                if group_id not in self.__non_default_group:
                    self.__non_default_group.add(group_id)
                if group_id in self.__data.disabled_group:
                    self.__data.disabled_group.add(group_id)
            return True

        def set_group_disable(self, group_id: int) -> bool:
            """在群group_id中禁用该插件

            Args:
                group_id (int): 群号

            Returns:
                bool: 返回True
            """
            if self.__default_status:
                if group_id not in self.__non_default_group:
                    self.__non_default_group.add(group_id)
                if group_id in self.__data.enabled_group:
                    self.__data.enabled_group.remove(group_id)
            else:
                if group_id in self.__non_default_group:
                    self.__non_default_group.remove(group_id)
                if group_id not in self.__data.disabled_group:
                    self.__data.disabled_group.addd(group_id)
            return True

        def set_usage(self, usage: Optional[str]) -> None:
            """设置插件用法

            Args:
                usage (Optional[str]): 用法
            """
            self.usage = usage

        def set_hidden(self, hidden: bool) -> None:
            """设置插件隐藏状态

            Args:
                hidden (bool): 隐藏状态
            """
            self.hidden = hidden

        def clean_group(self, group_set: Set[int]) -> None:
            """清理配置文件中冗余的群

            Args:
                group_set (Set[int]): 当前有效的群
            """
            self.__non_default_group &= group_set

    def __init__(self, file_path: Path) -> None:
        """PluginManager构造函数，管理全部插件

        Args:
            file_path (Path): 存储插件配置的文件夹名
        """
        self.__file_path = file_path
        self.__file_path.mkdir(exist_ok=True, parents=True)
        self.__plugin: Dict[str, PluginManager.Plugin] = {}
        """获取插件plugin_name对应的Plugin类
        """
        self.__plugin_aliases: Dict[str, str] = {}
        """建立插件别名到plugin_name的映射
        """
        plugin_files = self.__file_path.iterdir()
        for plugin_file in plugin_files:
            if plugin_file.suffix == ".json":
                plugin_name = plugin_file.name.removesuffix(".json")
                self.__plugin[plugin_name]: PluginManager.Plugin = PluginManager.Plugin(
                    file=plugin_file
                )

    async def init(self) -> List[Optional[str]]:
        """异步初始化所有Plugin类

        Returns:
            List[Optional[str]]: List中项为None时表示无异常，反之为表示异常的字符串
        """
        ret = await asyncio.gather(
            *[plugin.init() for plugin in self.__plugin.values()],
            return_exceptions=True,
        )
        for i, plugin in enumerate(self.__plugin.values()):
            if not ret[i]:
                for alias in plugin.all_name:
                    self.__plugin_aliases[alias] = plugin.plugin_name
        return ret

    def check_group_status(
        self, plugin_name: str, group_id: int, group_permission: int
    ) -> bool:
        """检测插件plugin_name是否响应该群，由group_manager调用

        Args:
            plugin_name (str): 插件名
            group_id (int): 群号
            group_permission (int): 群权限

        Returns:
            bool: 若响应，返回True
        """
        return (
            not (plugin := self.__plugin.get(plugin_name))
        ) or plugin.check_group_status(
            group_id=group_id, group_permission=group_permission
        )

    def check_user_status(self, plugin_name: str, user_permission: int) -> bool:
        """检测插件plugin_name是否响应用户，由user_manager调用

        Args:
            plugin_name (str): 插件名
            user_permission (int): 用户权限

        Returns:
            bool: 若响应，返回True
        """
        return (
            not (plugin := self.__plugin.get(plugin_name))
        ) or plugin.check_user_status(user_permission=user_permission)

    def check_permission(self, plugin_name: str, permission: int) -> bool:
        """检测permission的权限能否调用plugin_name插件

        Args:
            plugin_name (str): 插件名
            permission (int): 权限

        Returns:
            bool: 若权限足够返回True
        """
        return (
            not (plugin := self.__plugin.get(plugin_name))
        ) or plugin.check_permission(permission=permission)

    async def set_group_enable(self, plugin_name: str, group_id: int) -> bool:
        """启用group_id中的plugin_name插件

        Args:
            plugin_name (str): 插件名
            group_id (int): 群号

        Returns:
            bool: 若返回False则表示已被全局禁用，反之返回True
        """
        if (plugin := self.__plugin.get(plugin_name)) and plugin.set_group_enable(
            group_id
        ):
            await plugin.save()
            return True
        return False

    async def set_group_disable(self, plugin_name: str, group_id: int) -> bool:
        """禁用group_id中的plugin_name插件

        Args:
            plugin_name (str): 插件名
            group_id (int): 群号

        Returns:
            bool: 返回True
        """
        if (plugin := self.__plugin.get(plugin_name)) and plugin.set_group_disable(
            group_id
        ):
            await plugin.save()
            return True
        return False

    def get_plugin_usage(self, name: str) -> Optional[str]:
        """获取插件帮助，支持plugin_name与别名

        Args:
            name (str): 插件名或别名

        Returns:
            Optional[str]: 若找不到或该插件没有用法介绍，返回None
        """
        if name not in self.__plugin and name not in self.__plugin_aliases:
            return None
        if name not in self.__plugin:
            name = self.__plugin_aliases[name]
        return self.__plugin[name].usage

    def check_plugin(self, name: str) -> bool:
        """检测是否存在plugin_name的插件

        Args:
            name (str): 插件名

        Returns:
            bool: 若有，返回True
        """
        return name in self.__plugin

    def get_plugin_name_list(self) -> Set[str]:
        """获取插件名列表

        Returns:
            Set[str]: 插件名们
        """
        return self.__plugin.keys()

    def get_plugin_name(self, name: str) -> Optional[str]:
        """由插件名或别名获取插件名（plugin_name）

        Args:
            name (str): 插件名或别名

        Returns:
            Optional[str]: 若有返回插件名，反之None
        """
        if name in self.__plugin:
            return name
        return self.__plugin_aliases.get(name)

    def get_plugin_list(self) -> Set[Plugin]:
        """获取管理插件的Plugin类们

        Returns:
            Set[Plugin]: Plugin类们
        """
        return self.__plugin.values()

    async def clean_group(self, group_list: Union[List[int], Set[int]]) -> None:
        """清理配置文件中冗余的群

        Args:
            group_list (Union[List[int], Set[int]]): 当前有效的群
        """
        group_list = set(group_list)
        for plugin in self.__plugin.values():
            plugin.clean_group(group_list)
        await asyncio.gather(*[plugin.save() for plugin in self.__plugin.values()])

    def set_plugin_usage(self, plugin_name: str, usage: Optional[str]):
        """设定插件plugin_name的用法

        Args:
            plugin_name (str): 插件名
            usage (Optional[str]): 用法
        """
        if plugin_name not in self.__plugin:
            return
        self.__plugin[plugin_name].set_usage(usage=usage)

    def set_plugin_hidden(self, plugin_name: str, hidden: bool) -> None:
        """设定插件plugin_name的隐藏状态

        Args:
            plugin_name (str): 插件名
            hidden (bool): 隐藏状态
        """
        if plugin_name not in self.__plugin:
            return
        self.__plugin[plugin_name].set_hidden(hidden=hidden)

    def set_plugin_type(self, plugin_name: str, plugin_type: PluginType) -> None:
        """设定插件plugin_name的类型

        Args:
            plugin_name (str): 插件名
            plugin_type (PluginType): 插件类型
        """
        if plugin_name not in self.__plugin:
            return
        self.__plugin[plugin_name].set_plugin_type(type=plugin_type)

    async def enable_plugin(self, plugin_name: str):
        """全局启用插件plugin_name

        Args:
            plugin_name (str): 插件名
        """
        plugin = self.__plugin.get(plugin_name)
        if not plugin:
            return
        plugin.enable()
        await plugin.save()

    async def disable_plugin(self, plugin_name: str):
        """全局禁用插件

        Args:
            plugin_name (str): 插件名
        """
        plugin = self.__plugin.get(plugin_name)
        if not plugin:
            return
        plugin.disable()
        await plugin.save()

    async def add(
        self,
        plugin_name: str,
        name: str,
        aliases: List[str] = [],
        author: Optional[str] = None,
        version: Union[str, int, None] = None,
        category: Optional[str] = None,
        usage: Optional[str] = None,
        hidden: bool = False,
        default_status: bool = True,
        permission: int = NORMAL,
        plugin_type: PluginType = PluginType.All,
    ) -> None:
        """添加插件进PluginManager

        Args:
            plugin_name (str): 插件名
            name (str): 名字
            aliases (List[str], optional): 别名. Defaults to [].
            author (Optional[str], optional): 作者. Defaults to None.
            version (Union[str, int, None], optional): 版本. Defaults to None.
            category (Optional[str], optional): 类别. Defaults to None.
            usage (Optional[str], optional): 用法. Defaults to None.
            hidden (bool, optional): 隐藏状态. Defaults to False.
            default_status (bool, optional): 默认状态. Defaults to True.
            permission (int, optional): 所需权限. Defaults to NORMAL.
            plugin_type (PluginType, optional): 插件类型. Defaults to PluginType.All.
        """
        async with aiofiles.open(self.__file_path / f"{plugin_name}.json", "w") as f:
            await f.write(
                PluginManager.PluginAttr(
                    name=name,
                    aliases=aliases,
                    permission=permission,
                    global_status=True,
                    default_status=default_status,
                    enabled_group=set(),
                    disabled_group=set(),
                    category=category,
                    author=author,
                    version=version,
                ).json(ensure_ascii=False, indent=4)
            )

        self.__plugin[plugin_name] = PluginManager.Plugin(
            file=self.__file_path / f"{plugin_name}.json",
            usage=usage,
            hidden=hidden,
            plugin_type=plugin_type,
        )

    async def remove(self, plugin_name: set) -> None:
        """从PluginManager中移除插件

        Args:
            plugin_name (set): 插件名
        """
        if plugin_name in self.__plugin:
            del self.__plugin[plugin_name]
            (self.__file_path / f"{plugin_name}.json").unlink()
