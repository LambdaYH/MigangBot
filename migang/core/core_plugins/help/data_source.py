import random
from enum import Enum, unique
from pathlib import Path
from typing import Dict, List, Optional

from nonebot import get_driver
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot_plugin_htmlrender import template_to_pic
from nonebot_plugin_imageutils import BuildImage, text2image
from nonebot_plugin_imageutils.fonts import add_font
from pydantic import BaseModel

from migang.core.manager import (
    PluginManager,
    PluginType,
    group_manager,
    plugin_manager,
    task_manager,
    user_manager,
)
from migang.core.path import DATA_PATH, FONT_PATH

PLUGIN_HELP_BG = Path(__file__).parent / "image" / "plugin_help.png"
USER_HELP_PATH = DATA_PATH / "core" / "help" / "user_help_image"
GROUP_HELP_PATH = DATA_PATH / "core" / "help" / "group_help_image"
GROUP_TASK_PATH = DATA_PATH / "core" / "help" / "group_task_image"
USER_HELP_PATH.mkdir(exist_ok=True, parents=True)
GROUP_HELP_PATH.mkdir(exist_ok=True, parents=True)
GROUP_TASK_PATH.mkdir(exist_ok=True, parents=True)
for img in GROUP_HELP_PATH.iterdir():
    img.unlink()
for img in USER_HELP_PATH.iterdir():
    img.unlink()
for img in GROUP_TASK_PATH.iterdir():
    img.unlink()

TEMPLATE_PATH = Path(__file__).parent / "template"
LOGO_PATH = TEMPLATE_PATH / "menu" / "res" / "logo"


@get_driver().on_startup
async def _():
    await add_font("yz.ttf", FONT_PATH / "yz.ttf")


async def get_help_image(group_id: Optional[int], user_id: Optional[int], super: bool):
    """
    说明:
        生成帮助图片
    参数:
        :param group_id: 群号
    """
    return await _build_html_image(group_id, user_id, super)


def get_plugin_help(name: str) -> Optional[MessageSegment]:
    """
    说明:
        获取功能的帮助信息
    参数:
        :param msg: 功能cmd
        :param is_super: 是否为超级用户
    """
    if usage := plugin_manager.get_plugin_usage(name) or (
        usage := task_manager.get_task_usage(name)
    ):
        help_img = text2image(
            text=f"{usage}",
            fontname="yz.ttf",
            fontsize=24,
            padding=(40, 40),
            bg_color=(255, 255, 255, 0),
        )
        help_img = (
            BuildImage.open(PLUGIN_HELP_BG)
            .resize(size=(help_img.width, help_img.height))
            .draw_bbcode_text(
                xy=(40, 40),
                text=usage,
                fontsize=24,
                fontname="yz.ttf",
            )
        )
        return MessageSegment.image(help_img.save_jpg())
    return None


_sorted_data: Dict[str, List[PluginManager.Plugin]] = {}
_icon2str = {
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


@unique
class PluginStatus(Enum):
    enabled: int = 0
    disabled: int = 1
    group_disabled: int = 2
    not_authorized: int = 3


class MenuItem(BaseModel):
    plugin_name: str
    status: PluginStatus


def _sort_data():
    global _sorted_data
    if not _sorted_data:
        for plugin in plugin_manager.get_plugin_list():
            if plugin.hidden:
                continue
            if not _sorted_data.get(plugin.category):
                _sorted_data[plugin.category] = []
            _sorted_data[plugin.category].append(plugin)


async def _build_html_image(
    group_id: Optional[int], user_id: Optional[int], super: bool = False
) -> bytes:
    """生成帮助图片

    Args:
        group_id (Optional[int]): _description_
        user_id (Optional[int]): _description_
        super (bool, optional): _description_. Defaults to False.

    Returns:
        bytes: _description_
    """
    _sort_data()
    classify = {}
    logos = list(LOGO_PATH.iterdir())
    for menu, plugins in _sorted_data.items():
        for plugin in plugins:
            status = PluginStatus.enabled
            if not plugin.global_status:
                status = PluginStatus.group_disabled
            else:
                if group_id:
                    if not group_manager.check_plugin_permission(
                        plugin_name=plugin.plugin_name, group_id=group_id
                    ):
                        status = PluginStatus.not_authorized
                    else:
                        status = (
                            PluginStatus.enabled
                            if group_manager.check_group_plugin_status(
                                plugin_name=plugin.plugin_name, group_id=group_id
                            )
                            else PluginStatus.disabled
                        )
                elif user_id:
                    if not user_manager.check_plugin_permission(
                        plugin_name=plugin.plugin_name, user_id=user_id
                    ):
                        status = PluginStatus.not_authorized
                    else:
                        status = (
                            PluginStatus.enabled
                            if user_manager.check_user_plugin_status(
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
                classify[menu].append(MenuItem(plugin_name=plugin.name, status=status))
            else:
                classify[menu] = [MenuItem(plugin_name=plugin.name, status=status)]
    max_len = 0
    flag_index = -1
    max_data = None
    plugin_list = []
    for index, plu in enumerate(classify.keys()):
        if plu in _icon2str.keys():
            icon = _icon2str[plu]
        else:
            icon = "fa fa-pencil-square-o"
        logo = random.choice(logos)
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
        template_path=TEMPLATE_PATH / "menu",
        template_name="migang_menu.html",
        templates={
            "group": True if group_id else False,
            "plugin_list": plugin_list,
        },
        pages={
            "viewport": {"width": 1903, "height": 975},
        },
        wait=2,
    )
    return pic


class TaskMenuItem(BaseModel):
    name: str
    group_status: bool = False
    global_status: bool = False


async def get_task_image(group_id: int) -> bytes:
    """生成群被动图片

    Args:
        group_id (int): _description_

    Returns:
        bytes: _description_
    """
    task_list = []
    for task in task_manager.get_task_list():
        item = TaskMenuItem(
            name=task.name,
            group_status=group_manager.check_group_task_status(
                task_name=task.task_name, group_id=group_id
            ),
            global_status=task.global_status
            and group_manager.check_task_permission(
                task_name=task.task_name, group_id=group_id
            ),
        )
        task_list.append(item)
    pic = await template_to_pic(
        template_path=TEMPLATE_PATH / "task_menu",
        template_name="task_menu.html",
        templates={"task_list": task_list},
        pages={
            "viewport": {"width": 850, "height": 975},
        },
        wait=2,
    )
    return pic
