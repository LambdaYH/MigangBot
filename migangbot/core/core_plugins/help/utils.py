import os
import random
from typing import Dict, List, Optional

import aiofiles

from migangbot.core.decorator.singleton import Singleton
from migangbot.core.path import DATA_PATH, TEMPLATE_PATH
from migangbot.core.manager import (
    plugin_manager,
    PluginManager,
    group_manager,
    user_manager,
    PluginType,
)

from .data_class import Item, PluginStatus

USER_HELP_PATH = DATA_PATH / "core" / "help" / "user_help_image"
GROUP_HELP_PATH = DATA_PATH / "core" / "help" / "group_help_image"
USER_HELP_PATH.mkdir(exist_ok=True, parents=True)
GROUP_HELP_PATH.mkdir(exist_ok=True, parents=True)
for img in GROUP_HELP_PATH.iterdir():
    img.unlink()
for img in USER_HELP_PATH.iterdir():
    img.unlink()

LOGO_PATH = TEMPLATE_PATH / "menu" / "res" / "logo"


@Singleton
class HelpImageBuild:
    icon2str = {
        "通用": "fa fa-cog",
        "原神相关": "fa fa-circle-o",
        "常规插件": "fa fa-cubes",
        "联系管理员": "fa fa-envelope-o",
        "抽卡相关": "fa fa-credit-card-alt",
        "来点好康的": "fa fa-picture-o",
        "数据统计": "fa fa-bar-chart",
        "一些工具": "fa fa-shopping-cart",
        "商店": "fa fa-shopping-cart",
        "其它": "fa fa-tags",
        "群内小游戏": "fa fa-gamepad",
    }

    def __init__(self):
        self.__sort_data: Dict[str, List[PluginManager.Plugin]] = {}

    def __SortType(self):
        """
        说明:
            对插件按照菜单类型分类
        """
        if not self.__sort_data:
            for plugin in plugin_manager.GetPluginList():
                if not self.__sort_data.get(plugin.category):
                    self.__sort_data[plugin.category] = []
                self.__sort_data[plugin.category].append(plugin)

    async def BuildImage(
        self, group_id: Optional[int], user_id: Optional[int], super: bool
    ):
        help_image = (
            GROUP_HELP_PATH / f"{group_id}.png"
            if group_id
            else USER_HELP_PATH / f"{user_id}.png"
        )
        byt = await self.__BuildHTMLImage(
            group_id=group_id, user_id=user_id, super=super
        )
        async with aiofiles.open(help_image, "wb") as f:
            await f.write(byt)
        return byt

    async def __BuildHTMLImage(
        self, group_id: Optional[int], user_id: Optional[int], super: bool = False
    ) -> bytes:
        from nonebot_plugin_htmlrender import template_to_pic

        self.__SortType()
        classify = {}
        for menu, plugins in self.__sort_data.items():
            for plugin in plugins:
                status = PluginStatus.enabled
                if not plugin.global_status:
                    status = PluginStatus.group_disabled
                else:
                    if group_id:
                        if not group_manager.CheckPluginPermission(
                            plugin_name=plugin.plugin_name, group_id=group_id
                        ):
                            status = PluginStatus.not_authorized
                        else:
                            status = (
                                PluginStatus.enabled
                                if group_manager.CheckGroupPluginStatus(
                                    plugin_name=plugin.plugin_name, group_id=group_id
                                )
                                else PluginStatus.disabled
                            )
                    elif user_id:
                        if not user_manager.CheckPluginPermission(
                            plugin_name=plugin.plugin_name, user_id=user_id
                        ):
                            status = PluginStatus.not_authorized
                        else:
                            status = (
                                PluginStatus.enabled
                                if user_manager.CheckUserPluginStatus(
                                    plugin_name=plugin.plugin_name, user_id=user_id
                                )
                                else PluginStatus.disabled
                            )
                            type_block = {
                                PluginType.Group,
                                PluginType.GroupAdmin,
                                PluginType.SuperUser,
                            }
                            if super:
                                type_block.remove(PluginType.SuperUser)
                            if plugin.plugin_type in type_block:
                                status = PluginStatus.disabled
                if classify.get(menu):
                    classify[menu].append(Item(plugin_name=plugin.name, status=status))
                else:
                    classify[menu] = [Item(plugin_name=plugin.name, status=status)]
        max_len = 0
        flag_index = -1
        max_data = None
        plugin_list = []
        for index, plu in enumerate(classify.keys()):
            if plu in self.icon2str.keys():
                icon = self.icon2str[plu]
            else:
                icon = "fa fa-pencil-square-o"
            logo = LOGO_PATH / random.choice(os.listdir(LOGO_PATH))
            data = {
                "name": plu,
                "items": classify[plu],
                "icon": icon,
                "logo": str(logo.absolute()),
            }
            if len(classify[plu]) > max_len:
                max_len = len(classify[plu])
                flag_index = index
                max_data = data
            plugin_list.append(data)
        del plugin_list[flag_index]
        plugin_list.insert(0, max_data)
        pic = await template_to_pic(
            template_path=str((TEMPLATE_PATH / "menu").absolute()),
            template_name="migang_menu.html",
            templates={
                "group": True if group_id else False,
                "plugin_list": plugin_list,
            },
            pages={
                "viewport": {"width": 1903, "height": 975},
                "base_url": f"file://{TEMPLATE_PATH}",
            },
            wait=2,
        )
        return pic
