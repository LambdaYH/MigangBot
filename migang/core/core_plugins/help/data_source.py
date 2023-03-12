import math
import random
from pathlib import Path
from enum import Enum, unique
from typing import Dict, List, Optional

from pydantic import BaseModel
from pil_utils import BuildImage, text2image
from nonebot_plugin_htmlrender import template_to_pic
from nonebot.adapters.onebot.v11 import MessageSegment

from migang.core.path import DATA_PATH
from migang.core.manager import (
    PluginType,
    PluginManager,
    task_manager,
    user_manager,
    group_manager,
    plugin_manager,
)

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

colors = [
    "#eea2a4",
    "#621d34",
    "#e0c8d1",
    "#8b2671",
    "#142334",
    "#2b73af",
    "#93b5cf",
    "#2474b5",
    "#baccd9",
    "#1781b5",
    "#5cb3cc",
    "#57c3c2",
    "#1ba784",
    "#92b3a5",
    "#2bae85",
    "#83cbac",
    "#41ae3c",
    "#d0deaa",
    "#d2b42c",
    "#d2b116",
    "#f8df72",
    "#645822",
    "#ddc871",
    "#f9d770",
    "#d9a40e",
    "#b78b26",
    "#5d3d21",
    "#f8b37f",
    "#945833",
    "#e8b49a",
    "#a6522c",
    "#8b614d",
    "#f68c60",
    "#f6cec1",
    "#eeaa9c",
    "#862617",
    "#f2b9b2",
    "#f1908c",
]
color_len = len(colors)


async def get_help_image(group_id: Optional[int], user_id: Optional[int], super: bool):
    """
    说明:
        生成帮助图片
    参数:
        :param group_id: 群号
    """
    return await _build_html_image(group_id, user_id, super)


def get_plugin_help(name: str) -> Optional[str]:
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
        return usage
    return None


border = 18
inner_border = 20
top_border = 29
text_image_width = 160
text_image_padding = 15
line_width = 5
min_width = (
    text_image_width + border * 2 + text_image_padding * 2 + max(10, inner_border) * 2
)


def draw_usage(usage: str) -> Optional[MessageSegment]:
    help_img = text2image(
        text=usage,
        fontname="Yozai",
        fontsize=24,
        padding=(0, 0),
        bg_color=(255, 255, 255, 0),
    )
    color_candidates = ["#4586F3", "#EB4334", "#FBBD06", "#35AA53"]
    random.shuffle(color_candidates)

    help_img = text2image(
        text=usage,
        fontname="Yozai",
        fontsize=24,
        padding=(0, 0),
        bg_color=(255, 255, 255, 0),
    )
    bk = BuildImage.new(
        "RGBA",
        (
            max(help_img.width + border * 2 + inner_border * 2, min_width),
            help_img.height + border + top_border + inner_border * 2,
        ),
        color=(255, 255, 255),
    )
    # 边框左
    bk.draw_line(
        (border, top_border, border, bk.height - border),
        fill=color_candidates[0],
        width=line_width,
    )
    # 边框底
    bk.draw_line(
        (
            border - int(line_width / 2),
            bk.height - border,
            bk.width - border,
            bk.height - border,
        ),
        fill=color_candidates[1],
        width=line_width,
    )
    # 边框右
    bk.draw_line(
        (
            bk.width - border,
            bk.height - border + int(line_width / 2),
            bk.width - border,
            top_border,
        ),
        fill=color_candidates[2],
        width=line_width,
    )
    # 计算文字处于上边框的位置
    length = bk.width - border * 2
    start_idx = random.randint(
        10, length - 10 - text_image_padding - text_image_width - text_image_padding
    )
    # 上边框左半部分
    bk.draw_line(
        (border, top_border, start_idx + border, top_border),
        fill=color_candidates[3],
        width=line_width,
    )
    # 上边框右半部分
    bk.draw_line(
        (
            border
            + start_idx
            + text_image_padding
            + text_image_width
            + text_image_padding,
            top_border,
            bk.width - border + int(line_width / 2),
            top_border,
        ),
        fill=color_candidates[3],
        width=line_width,
    )
    # 把边框左被上边框遮住的一角画上
    bk.draw_line(
        (
            border,
            top_border - int(line_width / 2),
            border,
            top_border + int(line_width / 2),
        ),
        fill=color_candidates[0],
        width=line_width,
    )
    bk.paste(help_img, (border + inner_border, top_border + inner_border))
    random.shuffle(color_candidates)
    bk.draw_bbcode_text(
        (border + start_idx + text_image_padding, top_border - 30),
        text=f"[color={color_candidates[0]}]使[/color][color={color_candidates[1]}]用[/color][color={color_candidates[2]}]帮[/color][color={color_candidates[3]}]助[/color]",
        fontname="HONOR Sans CN",
        fontsize=40,
    )
    return MessageSegment.image(bk.save_png())


_sorted_data: Dict[str, List[PluginManager.Plugin]] = {}
_icon2str = {
    "通用": "fa fa-cog",
    "原神相关": "fa fa-circle-o",
    "常规插件": "fa fa-cubes",
    "基础功能": "fa fa-envelope-o",
    "抽卡相关": "fa fa-credit-card-alt",
    "好看的": "fa fa-picture-o",
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
    random.shuffle(colors)
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
    plugin_list = []
    for index, plu in enumerate(classify.keys()):
        icon = _icon2str.get(plu) or "fa fa-pencil-square-o"
        data = {
            "name": plu,
            "items": classify[plu],
            "icon": icon,
            "color": colors[index % color_len],
        }
        if len(classify[plu]) > max_len:
            max_len = len(classify[plu])
            flag_index = index
        plugin_list.append(data)
    plugin_list[flag_index], plugin_list[0] = plugin_list[0], plugin_list[flag_index]
    max_column_length = len(plugin_list[0]["items"])
    plugin_count = sum([len(plugin["items"]) for plugin in plugin_list])
    pic = await template_to_pic(
        template_path=TEMPLATE_PATH / "menu",
        template_name="migang_menu.html",
        templates={
            "group": True if group_id else False,
            "plugin_list": plugin_list,
            "column_count": math.ceil(
                (plugin_count + len(plugin_list)) / max_column_length
            ),
        },
        pages={
            "viewport": {"width": 1900, "height": 975},
        },
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
    )
    return pic
