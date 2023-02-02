from typing import Optional

from nonebot import get_driver, Driver
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot_plugin_imageutils import BuildImage
from nonebot_plugin_imageutils.fonts import add_font

from migangbot.core.path import IMAGE_PATH, FONT_PATH
from migangbot.core.manager import plugin_manager

from .utils import HelpImageBuild


_plugin_help_bg_file = IMAGE_PATH / "help" / "plugin_help.png"

driver: Driver = get_driver()


@driver.on_startup
async def _():
    await add_font("yz.ttf", FONT_PATH / "yz.ttf")


async def GetHelpImage(group_id: Optional[int], user_id: Optional[int], super: bool):
    """
    说明:
        生成帮助图片
    参数:
        :param group_id: 群号
    """
    return await HelpImageBuild().BuildImage(group_id, user_id, super)


def GetPluginHelp(name: str) -> Optional[MessageSegment]:
    """
    说明:
        获取功能的帮助信息
    参数:
        :param msg: 功能cmd
        :param is_super: 是否为超级用户
    """
    if usage := plugin_manager.GetPluginUsage(name):
        width = 0
        for x in usage.split("\n"):
            _width = len(x) * 24
            width = width if width > _width else _width
        height = len(usage.split("\n")) * 45
        help_img = (
            BuildImage.open(_plugin_help_bg_file)
            .resize(size=(width, height))
            .draw_bbcode_text(
                xy=(int(width * 0.048), int(height * 0.21)),
                text=usage,
                fontsize=24,
                fontname="yz.ttf",
            )
        )
        return MessageSegment.image(help_img.save_jpg())
    return None
