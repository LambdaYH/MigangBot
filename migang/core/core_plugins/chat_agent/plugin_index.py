from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable, Optional
from dataclasses import field, dataclass

from nonebot.plugin import get_plugin
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent
from nonebot.rule import (
    ToMeRule,
    RegexRule,
    CommandRule,
    EndswithRule,
    KeywordsRule,
    FullmatchRule,
    StartswithRule,
)

from migang.core.core_plugins.init.utils import get_plugin_list
from migang.core.manager import user_manager, group_manager, plugin_manager

from .help_intent import is_help_query
from .image_intent import (
    is_explicit_image_tool_query,
    is_general_image_understanding_query,
)

_SPACE_RE = re.compile(r"\s+")
_SPLIT_RE = re.compile(r"[\s,，。.:：;；/\\|()（）\\[\\]【】<>《》!?！？]+")


@dataclass(slots=True)
class PluginCommand:
    rule_type: str
    expression: str
    example: str
    requires_to_me: bool = False
    priority: int = 0


@dataclass(slots=True)
class PluginIndexEntry:
    plugin_name: str
    display_name: str
    aliases: list[str] = field(default_factory=list)
    category: str = ""
    usage: str = ""
    author: str = ""
    version: str = ""
    hidden: bool = False
    commands: list[PluginCommand] = field(default_factory=list)
    keywords: set[str] = field(default_factory=set)
    searchable_text: str = ""

    def short_label(self) -> str:
        if self.display_name == self.plugin_name:
            return self.display_name
        return f"{self.display_name} ({self.plugin_name})"

    def preferred_commands(self, limit: int = 3) -> list[PluginCommand]:
        priority = {
            "command": 0,
            "fullmatch": 1,
            "startswith": 2,
            "endswith": 3,
            "keyword": 4,
            "regex": 5,
        }
        return sorted(
            self.commands,
            key=lambda item: (priority.get(item.rule_type, 99), item.priority),
        )[:limit]

    def default_command(self) -> Optional[str]:
        for command in self.preferred_commands(limit=max(len(self.commands), 1)):
            if command.rule_type in {"command", "fullmatch", "startswith"}:
                return command.example
        return None


@dataclass(slots=True)
class PluginAvailability:
    available: bool
    status_text: str


@dataclass(slots=True)
class PluginSearchMatch:
    entry: PluginIndexEntry
    score: float
    availability: PluginAvailability


class PluginIndex:
    def __init__(self) -> None:
        self._entries: dict[str, PluginIndexEntry] = {}
        self._plugin_signature: tuple[str, ...] = ()

    def _get_signature(self) -> tuple[str, ...]:
        return tuple(sorted(plugin.name for plugin in get_plugin_list()))

    def refresh(self, force: bool = False) -> None:
        signature = self._get_signature()
        if not force and self._entries and signature == self._plugin_signature:
            return

        managed_plugins = {}
        try:
            managed_plugins = {
                plugin.plugin_name: plugin
                for plugin in plugin_manager.get_plugin_list()
                if hasattr(plugin, "plugin_name") and hasattr(plugin, "usage")
            }
        except Exception:
            managed_plugins = {}

        entries: dict[str, PluginIndexEntry] = {}
        for plugin in get_plugin_list():
            plugin_name = plugin.name
            module = plugin.module
            metadata = plugin.metadata
            managed = managed_plugins.get(plugin_name)

            display_name = (
                getattr(managed, "name", None)
                or (metadata.name if metadata and metadata.name else None)
                or getattr(module, "__plugin_name__", None)
                or plugin_name
            )
            usage = (
                getattr(managed, "usage", None)
                or (metadata.usage if metadata else None)
                or getattr(module, "__plugin_usage__", None)
                or ""
            )
            category = (
                getattr(managed, "category", None)
                or getattr(module, "__plugin_category__", None)
                or "功能"
            )
            author = (
                getattr(managed, "author", None)
                or (metadata.extra.get("author") if metadata else None)
                or getattr(module, "__plugin_author__", None)
                or ""
            )
            version = (
                str(getattr(managed, "version", "") or "")
                or str(metadata.extra.get("version", "") if metadata else "")
                or str(getattr(module, "__plugin_version__", "") or "")
            )
            hidden = bool(
                getattr(managed, "hidden", False)
                or getattr(module, "__plugin_hidden__", False)
            )

            aliases = {plugin_name, display_name}
            if managed and hasattr(managed, "all_name"):
                aliases.update(name for name in managed.all_name if name)
            aliases.update(getattr(module, "__plugin_aliases__", []) or [])
            aliases.discard("")

            commands = self._extract_commands(plugin_name)
            entry = PluginIndexEntry(
                plugin_name=plugin_name,
                display_name=display_name,
                aliases=sorted(aliases),
                category=category,
                usage=self._normalize_usage_text(usage),
                author=author,
                version=version,
                hidden=hidden,
                commands=commands,
            )
            entry.keywords = self._build_keywords(entry)
            entry.searchable_text = self._build_searchable_text(entry)
            entries[plugin_name] = entry

        self._entries = entries
        self._plugin_signature = signature

    def all_entries(self) -> list[PluginIndexEntry]:
        self.refresh()
        return list(self._entries.values())

    def user_visible_entries(
        self, event: Optional[MessageEvent] = None
    ) -> list[PluginIndexEntry]:
        self.refresh()
        result = []
        for entry in self._entries.values():
            if entry.hidden:
                continue
            if not entry.commands and not entry.usage:
                continue
            availability = self.get_availability(entry.plugin_name, event)
            if not availability.available:
                continue
            result.append(entry)
        return result

    def resolve(self, name_or_alias: str) -> Optional[PluginIndexEntry]:
        if not name_or_alias:
            return None
        self.refresh()
        normalized = self._normalize_text(name_or_alias)
        for entry in self._entries.values():
            if normalized == self._normalize_text(entry.plugin_name):
                return entry
            if normalized == self._normalize_text(entry.display_name):
                return entry
            if normalized in {self._normalize_text(alias) for alias in entry.aliases}:
                return entry
        plugin_name = plugin_manager.get_plugin_name(name_or_alias)
        if plugin_name:
            return self._entries.get(plugin_name)
        return None

    def search(
        self,
        query: str,
        limit: int = 5,
        event: Optional[MessageEvent] = None,
    ) -> list[PluginIndexEntry]:
        return [
            match.entry
            for match in self.search_matches(query=query, limit=limit, event=event)
        ]

    def search_matches(
        self,
        query: str,
        limit: int = 5,
        event: Optional[MessageEvent] = None,
    ) -> list[PluginSearchMatch]:
        self.refresh()
        normalized_query = self._normalize_text(query)
        if not normalized_query:
            return []

        query_keywords = self._keywords_from_text(query)
        scored: list[PluginSearchMatch] = []
        for entry in self._entries.values():
            score = self._score_entry(entry, normalized_query, query_keywords)
            if score <= 0:
                continue
            availability = self.get_availability(entry.plugin_name, event)
            if availability.available:
                score += 1
            scored.append(
                PluginSearchMatch(
                    entry=entry,
                    score=score,
                    availability=availability,
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    def get_availability(
        self, plugin_name: str, event: Optional[MessageEvent]
    ) -> PluginAvailability:
        if event is None:
            return PluginAvailability(True, "未校验当前会话状态")
        try:
            if isinstance(event, GroupMessageEvent):
                if not group_manager.check_plugin_permission(
                    plugin_name, event.group_id
                ):
                    return PluginAvailability(False, "当前群权限不足")
                if not group_manager.check_group_plugin_status(
                    plugin_name, event.group_id
                ):
                    return PluginAvailability(False, "当前群未启用")
                return PluginAvailability(True, "当前群可用")

            if not user_manager.check_plugin_permission(plugin_name, event.user_id):
                return PluginAvailability(False, "当前用户权限不足")
            if not user_manager.check_user_plugin_status(plugin_name, event.user_id):
                return PluginAvailability(False, "当前私聊不可用")
            return PluginAvailability(True, "当前私聊可用")
        except Exception:
            return PluginAvailability(True, "未校验当前会话状态")

    def render_search_results(
        self,
        query: str,
        limit: int = 5,
        event: Optional[MessageEvent] = None,
    ) -> str:
        visible_plugin_names = {
            entry.plugin_name for entry in self.user_visible_entries(event)
        }
        matches = [
            match
            for match in self.search_matches(query, limit=limit * 3, event=event)
            if match.entry.plugin_name in visible_plugin_names
        ][:limit]
        return self.render_match_results(query=query, matches=matches)

    def render_match_results(
        self,
        query: str,
        matches: list[PluginSearchMatch],
    ) -> str:
        if not matches:
            return f"没有找到与“{query}”相关的插件。"

        lines = [f"与“{query}”最相关的插件："]
        for index, match in enumerate(matches, start=1):
            entry = match.entry
            availability = match.availability
            lines.append(
                f"{index}. {entry.short_label()} | 分类: {entry.category or '功能'} | 状态: {availability.status_text}"
            )
            if entry.aliases:
                alias_text = ", ".join(
                    alias
                    for alias in entry.aliases
                    if alias not in {entry.plugin_name, entry.display_name}
                )
                if alias_text:
                    lines.append(f"   别名: {alias_text}")
            if entry.commands:
                commands = " / ".join(
                    command.example for command in entry.preferred_commands()
                )
                lines.append(f"   推荐触发词: {commands}")
            if entry.usage:
                lines.append(f"   用法: {self._truncate(entry.usage, 120)}")
        return "\n".join(lines)

    def render_plugin_detail(
        self, name_or_alias: str, event: Optional[MessageEvent] = None
    ) -> str:
        entry = self.resolve(name_or_alias)
        if entry is None:
            return f"找不到插件“{name_or_alias}”。"

        availability = self.get_availability(entry.plugin_name, event)
        lines = [
            f"插件: {entry.short_label()}",
            f"状态: {availability.status_text}",
            f"分类: {entry.category or '功能'}",
        ]
        if entry.aliases:
            lines.append(f"别名: {', '.join(entry.aliases)}")
        if entry.author:
            lines.append(f"作者: {entry.author}")
        if entry.version:
            lines.append(f"版本: {entry.version}")
        if entry.commands:
            lines.append("可识别触发词:")
            for command in entry.preferred_commands(limit=8):
                suffix = " | 需要@Bot" if command.requires_to_me else ""
                lines.append(f"- {command.example} [{command.rule_type}]{suffix}")
        if entry.usage:
            lines.append(f"用法说明: {entry.usage}")
        return "\n".join(lines)

    def render_prompt_context(
        self,
        query: str,
        limit: int = 4,
        event: Optional[MessageEvent] = None,
        has_image: bool = False,
    ) -> str:
        if has_image and is_general_image_understanding_query(query):
            return (
                "当前消息包含图片，这更像直接看图问题。"
                "第一反应应直接基于图片内容回答，不要先调用插件。"
                "只有用户明确要求二维码、扫码、OCR、提取文字、翻译图片、识图，"
                "或者你已经尝试看图但确认无法仅靠视觉回答时，"
                "才调用 search_project_plugins、inspect_project_plugin 或 invoke_project_plugin。"
            )
        if has_image and is_explicit_image_tool_query(query):
            return "当前消息包含图片，且用户明确要求图片工具处理，可以检索相关插件。"
        if is_help_query(query):
            return "这更像帮助咨询问题，优先调用 query_help_plugin，而不是 search_project_plugins。"

        results = [
            entry
            for entry in self.search(query, limit=limit * 3, event=event)
            if entry in self.user_visible_entries(event)
        ][:limit]
        if not results:
            return "暂无明显相关插件。"
        lines = []
        for entry in results:
            availability = self.get_availability(entry.plugin_name, event)
            line = f"[{entry.plugin_name}] {entry.display_name} | {availability.status_text}"
            if entry.commands:
                line += " | 触发词: " + " / ".join(
                    command.example for command in entry.preferred_commands(limit=2)
                )
            if entry.usage:
                line += " | 用法: " + self._truncate(entry.usage, 90)
            lines.append(line)
        return "\n".join(lines)

    def _extract_commands(self, plugin_name: str) -> list[PluginCommand]:
        plugin = get_plugin(plugin_name)
        if plugin is None:
            return []

        commands: list[PluginCommand] = []
        seen = set()
        for matcher in plugin.matcher:
            requires_to_me = any(
                isinstance(dep.call, ToMeRule) for dep in matcher.rule.checkers
            )
            for dep in matcher.rule.checkers:
                extracted = self._extract_commands_from_checker(
                    dep.call, requires_to_me, matcher.priority
                )
                for command in extracted:
                    dedupe_key = (
                        command.rule_type,
                        command.expression,
                        command.example,
                        command.requires_to_me,
                    )
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    commands.append(command)
        return commands

    def _extract_commands_from_checker(
        self, checker: object, requires_to_me: bool, priority: int
    ) -> list[PluginCommand]:
        if isinstance(checker, CommandRule):
            return [
                PluginCommand(
                    rule_type="command",
                    expression=command,
                    example=command,
                    requires_to_me=requires_to_me,
                    priority=priority,
                )
                for command in self._flatten_rule_values(checker.cmds)
            ]
        if isinstance(checker, FullmatchRule):
            return [
                PluginCommand(
                    rule_type="fullmatch",
                    expression=text,
                    example=text,
                    requires_to_me=requires_to_me,
                    priority=priority,
                )
                for text in self._flatten_rule_values(checker.msg)
            ]
        if isinstance(checker, StartswithRule):
            return [
                PluginCommand(
                    rule_type="startswith",
                    expression=text,
                    example=text,
                    requires_to_me=requires_to_me,
                    priority=priority,
                )
                for text in self._flatten_rule_values(checker.msg)
            ]
        if isinstance(checker, EndswithRule):
            return [
                PluginCommand(
                    rule_type="endswith",
                    expression=text,
                    example=text,
                    requires_to_me=requires_to_me,
                    priority=priority,
                )
                for text in self._flatten_rule_values(checker.msg)
            ]
        if isinstance(checker, KeywordsRule):
            return [
                PluginCommand(
                    rule_type="keyword",
                    expression=text,
                    example=text,
                    requires_to_me=requires_to_me,
                    priority=priority,
                )
                for text in self._flatten_rule_values(checker.keywords)
            ]
        if isinstance(checker, RegexRule):
            regex = (
                checker.regex.pattern
                if hasattr(checker.regex, "pattern")
                else str(checker.regex)
            )
            return [
                PluginCommand(
                    rule_type="regex",
                    expression=regex,
                    example=regex,
                    requires_to_me=requires_to_me,
                    priority=priority,
                )
            ]
        return []

    def _build_searchable_text(self, entry: PluginIndexEntry) -> str:
        parts = [
            entry.plugin_name,
            entry.display_name,
            *entry.aliases,
            entry.category,
            entry.usage,
            entry.author,
            entry.version,
            *(command.expression for command in entry.commands),
            *(command.example for command in entry.commands),
        ]
        return "\n".join(part for part in parts if part)

    def _build_keywords(self, entry: PluginIndexEntry) -> set[str]:
        keywords = set()
        for text in [
            entry.plugin_name,
            entry.display_name,
            *entry.aliases,
            entry.category,
            entry.usage,
            *(command.expression for command in entry.commands),
            *(command.example for command in entry.commands),
        ]:
            keywords.update(self._keywords_from_text(text))
        return keywords

    def _score_entry(
        self, entry: PluginIndexEntry, normalized_query: str, query_keywords: set[str]
    ) -> float:
        score = 0.0
        primary_names = [entry.plugin_name, entry.display_name, *entry.aliases]
        primary_names = [self._normalize_text(name) for name in primary_names if name]
        command_texts = [
            self._normalize_text(command.expression or command.example)
            for command in entry.commands
        ]

        if normalized_query in primary_names:
            score += 100
        if any(normalized_query and normalized_query in name for name in primary_names):
            score += 45
        if any(name and name in normalized_query for name in primary_names):
            score += 24
        if any(
            normalized_query and normalized_query in command_text
            for command_text in command_texts
        ):
            score += 16
        if normalized_query in self._normalize_text(entry.usage):
            score += 12
        if normalized_query in self._normalize_text(entry.category):
            score += 6

        if query_keywords:
            overlap = query_keywords & entry.keywords
            score += len(overlap) * 3

        candidates = [entry.searchable_text, *primary_names, *command_texts]
        fuzzy = max(
            (
                SequenceMatcher(
                    None, normalized_query, self._normalize_text(candidate)
                ).ratio()
                for candidate in candidates
                if candidate
            ),
            default=0.0,
        )
        score += fuzzy * 20
        return score

    def _normalize_usage_text(self, usage: str) -> str:
        if not usage:
            return ""
        text = usage.replace("[md]", "").replace("[html]", "").replace("[text]", "")
        text = re.sub(r"\[width=\d+(?:[,，]height=\d+)?\]", "", text)
        return _SPACE_RE.sub(" ", text).strip()

    def _normalize_text(self, text: str) -> str:
        return _SPACE_RE.sub(" ", str(text or "").strip().lower())

    def _keywords_from_text(self, text: str) -> set[str]:
        normalized = self._normalize_text(text)
        if not normalized:
            return set()
        tokens = {token for token in _SPLIT_RE.split(normalized) if token}
        compact = re.sub(r"\s+", "", normalized)
        if compact:
            tokens.add(compact)
        if len(compact) >= 2:
            max_size = min(4, len(compact))
            for size in range(2, max_size + 1):
                for index in range(len(compact) - size + 1):
                    tokens.add(compact[index : index + size])
        return tokens

    def _flatten_rule_values(self, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, re.Pattern):
            return [value.pattern]
        if isinstance(value, str):
            return [value]
        if isinstance(value, Iterable):
            result: list[str] = []
            for item in value:
                result.extend(self._flatten_rule_values(item))
            return result
        return [str(value)]

    def _truncate(self, text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."


plugin_index = PluginIndex()
