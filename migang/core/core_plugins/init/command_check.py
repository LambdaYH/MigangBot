"""检测指令冲突，执行指令替换，指令屏蔽等
"""

from pathlib import Path
from typing import Set, Union, List, Dict, DefaultDict, Tuple, Optional
from collections import defaultdict
from io import BytesIO
import re

from nonebot.dependencies import Dependent
from nonebot.matcher import Matcher
from nonebot.log import logger
from nonebot.permission import SuperUser, SUPERUSER
from nonebot_plugin_imageutils import text2image
from nonebot.plugin import Plugin
from nonebot import on_command, require, get_plugin
from nonebot.params import CommandArg
from nonebot.rule import (
    to_me,
    ToMeRule,
    FullmatchRule,
    CommandRule,
    StartswithRule,
    EndswithRule,
    RegexRule,
    KeywordsRule,
)
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    MessageEvent,
    GroupMessageEvent,
    PrivateMessageEvent,
    MessageSegment,
)
import aiofiles

from migang.core.utils.file_operation import async_load_data, async_save_data
from migang.core.manager import (
    group_manager,
    plugin_manager,
    user_manager,
    core_data_path,
)

from .utils import get_plugin_list

_file = core_data_path / "command_substitution.json"


class Item:
    def __init__(self, plugin: Plugin, command_type: str) -> None:
        plugin: Plugin = plugin
        command_type: str = command_type

    def __hash__(self) -> int:
        return hash(self.plugin.nam)


async def sub_command(checkers: Set[Dependent[bool]], source_cmd: str, target_cmd: str):
    for dep in checkers:
        if isinstance(dep.call, RegexRule):
            if source_cmd == dep.call.regex:
                dep.call.regex = target_cmd
        elif isinstance(dep.call, CommandRule):
            need_sub = False
            for cmd_tuple in dep.call.cmds:
                if source_cmd in cmd_tuple:
                    need_sub = True
                    break
            if not need_sub:
                continue
            cmds_set: Set[Tuple[str, ...]] = set(dep.call.cmds)
            for cmd_tuple in list(cmds_set):
                if source_cmd in cmd_tuple:
                    cmd_set = set(cmd_tuple)
                    cmd_set.remove(source_cmd)
                    cmd_set.add(target_cmd)
                    cmds_set.remove(cmd_tuple)  # 移除旧的
                    cmds_set.add(tuple(cmd_set))  # 放进新指令
            dep.call.cmds = tuple(cmds_set)
        elif isinstance(dep.call, KeywordsRule):
            if source_cmd in dep.call.keywords:
                keywords_set = set(dep.call.keywords)
                keywords_set.remove(source_cmd)
                keywords_set.add(target_cmd)
                dep.call.keywords = tuple(keywords_set)
        elif (
            isinstance(dep.call, FullmatchRule)
            or isinstance(dep.call, StartswithRule)
            or isinstance(dep.call, EndswithRule)
        ):
            if source_cmd in dep.call.msg:
                msg_set = set(dep.call.msg)
                msg_set.remove(source_cmd)
                msg_set.add(target_cmd)
                dep.call.msg = tuple(msg_set)


type_to_class = {
    "fullmatch": FullmatchRule,
    "command": CommandRule,
    "startswith": StartswithRule,
    "endswith": EndswithRule,
    "regex": RegexRule,
    "keywords": KeywordsRule,
}


def get_checkers(plugin: Plugin, type_: str):
    ret: Set[Set[Dependent[bool]]]
    for matcher in plugin.matcher:
        for checker in matcher.rule.checkers:
            if isinstance(checker.call, type_to_class[type_]):
                ret.add(checker)
    return ret


async def check_command():
    command_subs: Dict[
        str, Dict[str, Dict[str, Optional[str]]]
    ] = await async_load_data(_file)
    """插件名-类型-命令：命令替换/None
    """

    commands_check: DefaultDict[str, Dict[str, Plugin]] = defaultdict(lambda: dict())
    """类型-命令-插件集
    """
    plugins = get_plugin_list()
    name_to_plugin = {}
    for plugin in plugins:
        name_to_plugin[plugin.name] = plugin

    # 先替换
    for plugin_name, types in command_subs.items():
        if plugin_name not in name_to_plugin:
            continue
        for type_, cmds in types.items():
            for src_cmd, dst_cmd in cmds.items():
                if dst_cmd is None:
                    continue
                sub_command(get_checkers(name_to_plugin[plugin_name], type_), src_cmd, dst_cmd)
                logger.info(f"已将插件【{plugin_name}】的[{type_}]指令 {src_cmd} 替换为 {dst_cmd}")

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

    # 先检查所有指令，检查是否有冲突
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
                    + f"】存在指令 {cmd} 冲突"
                )
                for plugin in plugins:
                    if plugin.name not in command_subs:
                        command_subs[plugin.name] = {}
                    if type_ not in command_subs[plugin.name]:
                        command_subs[plugin.name][type_] = {}
                    command_subs[plugin.name][type_][cmd] = None
    await async_save_data(command_subs, _file)

    # 冲突指令替换
    # Todo
