import re
import math
import random
from io import BytesIO
from pathlib import Path
from enum import Enum, unique
from typing import Dict, List, Optional

from nonebot import require
from pydantic import BaseModel
from nonebot.utils import run_sync
from pil_utils import BuildImage, text2image
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

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic, html_to_pic, template_to_pic

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


async def get_help_image(
    group_id: Optional[int], user_id: Optional[int], super_user: bool
):
    """
    说明:
        生成帮助图片
    参数:
        :param group_id: 群号
    """
    return await _build_html_image(group_id, user_id, super_user)


def get_plugin_help(name: str) -> Optional[str]:
    """
    说明:
        获取功能的帮助信息
    参数:
        :param msg: 功能cmd
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


async def draw_usage(usage: str) -> Optional[MessageSegment]:
    png = await build_usage_png(usage)
    return MessageSegment.image(png)


async def build_usage_png(usage: str) -> bytes:
    """将使用说明渲染为 PNG 字节，供图片与网页复用"""
    help_img = text2image(
        text=usage,
        fontname="Yozai",
        fontsize=24,
        padding=(0, 0),
        bg_color=(255, 255, 255, 0),
    )
    color_candidates = ["#4586F3", "#EB4334", "#FBBD06", "#35AA53"]
    random.shuffle(color_candidates)
    if usage.startswith("[md]"):
        usage = usage.removeprefix("[md]").lstrip()
        width = 600
        if match := re.match(r"^\[width=(\d+)\]", usage):
            usage = usage.removeprefix(match.group(0)).lstrip()
            width = int(match.group(1))
        help_img = BuildImage.open(BytesIO(await md_to_pic(usage, width=width)))
    elif usage.startswith("[html]"):
        usage = usage.removeprefix("[html]").lstrip()
        kwargs = {}
        if match := re.match(r"^\[width=(\d+)[,，]height=(\d+)\]", usage):
            usage = usage.removeprefix(match.group(0)).lstrip()
            kwargs["viewport"] = {
                "width": int(match.group(1)),
                "height": int(match.group(2)),
            }
        help_img = BuildImage.open(BytesIO(await html_to_pic(usage, **kwargs)))
    else:
        if usage.startswith("[text]"):
            usage = usage.removeprefix("[text]").lstrip()
        help_img = text2image(
            text=usage,
            fontname="Yozai",
            fontsize=24,
            padding=(0, 0),
            bg_color=(255, 255, 255),
        )

    @run_sync
    def _draw():
        bk = BuildImage.new(
            "RGBA",
            (
                max(help_img.width + border * 2 + inner_border * 2, min_width),
                help_img.height + border + top_border + inner_border * 2,
            ),
            color=(255, 255, 255),
        )
        bk.draw_line(
            (border, top_border, border, bk.height - border),
            fill=color_candidates[0],
            width=line_width,
        )
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
        length = bk.width - border * 2
        start_idx = random.randint(
            10, length - 10 - text_image_padding - text_image_width - text_image_padding
        )
        bk.draw_line(
            (border, top_border, start_idx + border, top_border),
            fill=color_candidates[3],
            width=line_width,
        )
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
        return bk.save_png()

    return await _draw()


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
    if not _sorted_data:
        for plugin in plugin_manager.get_plugin_list():
            if plugin.hidden:
                continue
            if not _sorted_data.get(plugin.category):
                _sorted_data[plugin.category] = []
            _sorted_data[plugin.category].append(plugin)


def get_help_menu_context(
    group_id: Optional[int], user_id: Optional[int], super_user: bool = False
) -> Dict:
    """构建帮助菜单模板上下文（网页/图片复用）"""
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
                        if super_user:
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
    max_column_length = len(plugin_list[0]["items"]) if plugin_list else 1
    plugin_count = (
        sum([len(plugin["items"]) for plugin in plugin_list]) if plugin_list else 0
    )
    return {
        "group": True if group_id else False,
        "plugin_list": plugin_list,
        "column_count": min(
            math.ceil((plugin_count + len(plugin_list)) / max_column_length), 4
        )
        if plugin_list
        else 1,
    }


async def _build_html_image(
    group_id: Optional[int], user_id: Optional[int], super_user: bool = False
) -> bytes:
    """生成帮助图片（基于模板上下文）"""
    ctx = get_help_menu_context(
        group_id=group_id, user_id=user_id, super_user=super_user
    )
    pic = await template_to_pic(
        template_path=TEMPLATE_PATH / "menu",
        template_name="migang_menu.html",
        templates=ctx,
        type="jpeg",
        quality=76,
        pages={
            "viewport": {"width": 1900, "height": 975},
        },
        device_scale_factor=None,
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
        type="jpeg",
        quality=80,
        pages={
            "viewport": {"width": 850, "height": 975},
        },
        device_scale_factor=None,
    )
    return pic
