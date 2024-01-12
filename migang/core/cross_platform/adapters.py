from nonebot import require
from nonebot.plugin import inherit_supported_adapters

require("nonebot_plugin_alconna")
require("nonebot_plugin_session")
require("nonebot_plugin_saa")

supported_adapters = inherit_supported_adapters(
    "nonebot_plugin_alconna", "nonebot_plugin_session", "nonebot_plugin_saa"
)
