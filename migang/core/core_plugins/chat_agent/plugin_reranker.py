from __future__ import annotations

import re
import json
from typing import Iterable

from nonebot.log import logger
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from .settings import ChatAgentSettings
from .plugin_index import PluginSearchMatch

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class PluginReranker:
    def __init__(self) -> None:
        self._llm: ChatOpenAI | None = None
        self._llm_signature: tuple | None = None

    def should_rerank(self, query: str, matches: list[PluginSearchMatch]) -> bool:
        settings = ChatAgentSettings.load()
        if not settings.plugin_rerank_enabled:
            return False
        if len(query.strip()) < 3:
            return False
        if len(matches) < 2:
            return False

        top_gap = matches[0].score - matches[1].score
        if top_gap > float(settings.plugin_rerank_score_gap):
            return False

        strong_exact_hit = matches[0].score >= 90 and top_gap >= 3
        return not strong_exact_hit

    async def rerank(
        self,
        query: str,
        matches: list[PluginSearchMatch],
    ) -> list[PluginSearchMatch]:
        settings = ChatAgentSettings.load()
        top_n = max(2, min(settings.plugin_rerank_top_n, len(matches)))
        candidates = matches[:top_n]
        if len(candidates) < 2:
            return matches

        llm = self._get_llm(settings)
        candidate_block = self._build_candidate_block(candidates)
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content=(
                        "你负责在候选插件中选择最符合用户意图的一个。"
                        "只允许从候选项中选择，不要编造新插件。"
                        '请只返回 JSON，例如 {"plugin_name":"weather","reason":"..."}。'
                    )
                ),
                HumanMessage(
                    content=(
                        f"用户请求：{query}\n" f"候选插件：\n{candidate_block}\n" "请选择最匹配的插件。"
                    )
                ),
            ]
        )
        plugin_name = self._parse_plugin_name(
            getattr(response, "content", ""),
            [candidate.entry.plugin_name for candidate in candidates],
        )
        if not plugin_name:
            logger.warning("插件重排未解析出有效结果，回退到本地排序")
            return matches

        winner = next(
            (
                candidate
                for candidate in candidates
                if candidate.entry.plugin_name == plugin_name
            ),
            None,
        )
        if winner is None:
            logger.warning("插件重排命中了候选集外的插件，回退到本地排序")
            return matches

        remaining = [
            candidate
            for candidate in matches
            if candidate.entry.plugin_name != plugin_name
        ]
        logger.info(f"插件检索触发 LLM 重排，优先选择: {plugin_name}")
        return [winner, *remaining]

    def _get_llm(self, settings: ChatAgentSettings) -> ChatOpenAI:
        api_key = settings.api_keys[0] if settings.api_keys else ""
        model = settings.plugin_rerank_model or settings.model
        signature = (
            model,
            settings.api_base,
            api_key,
            settings.timeout,
            settings.reasoning_split,
        )
        if self._llm is not None and self._llm_signature == signature:
            return self._llm

        kwargs = {
            "model": model,
            "temperature": 0,
            "max_tokens": 128,
            "request_timeout": settings.timeout,
            "api_key": api_key,
            "streaming": False,
            "extra_body": {
                "reasoning_split": settings.reasoning_split,
            },
        }
        if settings.api_base:
            kwargs["base_url"] = settings.api_base

        self._llm = ChatOpenAI(**kwargs)
        self._llm_signature = signature
        return self._llm

    def _build_candidate_block(self, matches: Iterable[PluginSearchMatch]) -> str:
        lines: list[str] = []
        for index, match in enumerate(matches, start=1):
            entry = match.entry
            commands = " / ".join(
                command.example for command in entry.preferred_commands(limit=2)
            )
            lines.append(
                f"{index}. plugin_name={entry.plugin_name}; display_name={entry.display_name}; "
                f"category={entry.category or '功能'}; commands={commands or '无'}; "
                f"usage={entry.usage or '无'}"
            )
        return "\n".join(lines)

    def _parse_plugin_name(
        self,
        content: object,
        valid_plugin_names: list[str],
    ) -> str:
        text = str(content or "").strip()
        if not text:
            return ""

        match = _JSON_BLOCK_RE.search(text)
        if match:
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                plugin_name = str(payload.get("plugin_name", "")).strip()
                if plugin_name in valid_plugin_names:
                    return plugin_name

        for plugin_name in valid_plugin_names:
            if plugin_name in text:
                return plugin_name
        return ""


plugin_reranker = PluginReranker()
