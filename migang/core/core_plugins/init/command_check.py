"""
检测指令冲突
"""
import re
from collections import defaultdict
from typing import Dict, Tuple, Union, DefaultDict

from nonebot.log import logger
from nonebot.plugin import Plugin
from nonebot.rule import (
    RegexRule,
    CommandRule,
    EndswithRule,
    KeywordsRule,
    FullmatchRule,
    StartswithRule,
)

from .utils import get_plugin_list


def check_command():
    commands_check: DefaultDict[str, Dict[str, Plugin]] = defaultdict(dict)
    """类型-命令-插件集
    """

    def add(
        type_: str, plugin: Plugin, cmds: Union[str, Tuple[str], Tuple[Tuple[str]]]
    ):
        if isinstance(cmds, str):
            cmds = [cmds]
        if isinstance(cmds, re.Pattern):
            cmds = [cmds.pattern]
        for cmd in cmds:
            if isinstance(cmd, str):
                cmd = [cmd]
            for c in cmd:
                if c not in commands_check[type_]:
                    commands_check[type_][c] = set()
                commands_check[type_][c].add(plugin)

    plugins = get_plugin_list()
    # 检查所有指令，检查是否有冲突
    for plugin in plugins:
        for matcher in plugin.matcher:
            for dep in matcher.rule.checkers:
                if isinstance(dep.call, FullmatchRule):
                    add("fullmatch", plugin, dep.call.msg)
                elif isinstance(dep.call, CommandRule):
                    add("command", plugin, dep.call.cmds)
                elif isinstance(dep.call, StartswithRule):
                    add("startswith", plugin, dep.call.msg)
                elif isinstance(dep.call, EndswithRule):
                    add("endswith", plugin, dep.call.msg)
                elif isinstance(dep.call, RegexRule):
                    add("regex", plugin, dep.call.regex)
                elif isinstance(dep.call, KeywordsRule):
                    add("keywords", plugin, dep.call.keywords)
    for type_, cmds in commands_check.items():
        for cmd, plugins in cmds.items():
            if len(plugins) >= 2:
                logger.warning(
                    "插件【"
                    + "/".join([plugin.name for plugin in plugins])
                    + f"】的【{type_}】指令【{cmd}】存在冲突"
                )
