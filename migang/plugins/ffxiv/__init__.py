from pathlib import Path

import nonebot
from nonebot.plugin import PluginMetadata

__plugin_hidden__ = True
__plugin_meta__ = PluginMetadata(
    name="最终幻想14相关插件",
    description="最终幻想14相关插件",
    usage="""
usage：
    时尚品鉴作业：/nn
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)

nonebot.load_plugins(str(Path(__file__).parent.resolve()))
