from __future__ import annotations

from dataclasses import dataclass

from migang.core import ConfigItem
from migang.core.manager import config_manager

from .config import sync_get_agent_config

CHAT_AGENT_CONFIGS = (
    ConfigItem(
        key="personality",
        default_value="她叫{bot_name}，是一个搭配师",
        description="对话人格预设",
    ),
    ConfigItem(key="api_base", description="若使用第三方 OpenAI API，填写这个"),
    ConfigItem(
        key="api_keys",
        initial_value=[],
        default_value=[],
        description="OpenAI API Key 列表",
    ),
    ConfigItem(
        key="memory_short_length",
        initial_value=12,
        default_value=12,
        description="短期会话记忆长度",
    ),
    ConfigItem(
        key="memory_max_length",
        initial_value=24,
        default_value=24,
        description="长期记忆最大长度",
    ),
    ConfigItem(
        key="timeout",
        initial_value=60,
        default_value=60,
        description="OpenAI 请求超时时间",
    ),
    ConfigItem(
        key="ignore_prefix",
        initial_value=["/"],
        description="以此前缀开头的消息不被处理",
    ),
    ConfigItem(
        key="max_response_per_msg",
        initial_value=5,
        default_value=5,
        description="每条消息最大响应次数",
    ),
    ConfigItem(
        key="reasoning_split",
        initial_value=True,
        default_value=True,
        description="是否启用 MiniMax reasoning_split，便于分离思考内容",
    ),
    ConfigItem(
        key="plugin_rerank_enabled",
        initial_value=True,
        default_value=True,
        description="插件检索结果接近时，是否启用 LLM 重排",
    ),
    ConfigItem(
        key="plugin_rerank_model",
        initial_value="",
        default_value="",
        description="插件重排模型；留空时复用主对话模型",
    ),
    ConfigItem(
        key="plugin_rerank_top_n",
        initial_value=4,
        default_value=4,
        description="触发重排时参与 LLM 判断的候选插件数量",
    ),
    ConfigItem(
        key="plugin_rerank_score_gap",
        initial_value=5.0,
        default_value=5.0,
        description="本地 top1 与 top2 分差小于等于该值时触发重排",
    ),
    ConfigItem(
        key="model",
        default_value="gpt-3.5-turbo",
        initial_value="gpt-3.5-turbo",
        description="对话模型",
    ),
    ConfigItem(
        key="reply_max_tokens",
        initial_value=1024,
        default_value=1024,
        description="单次回复最大 token 数",
    ),
    ConfigItem(
        key="temperature",
        initial_value=0.4,
        default_value=0.4,
        description="温度越高越随机",
    ),
    ConfigItem(key="top_p", initial_value=1, default_value=1),
    ConfigItem(
        key="frequency_penalty",
        initial_value=0.4,
        default_value=0.4,
        description="复读惩罚",
    ),
    ConfigItem(
        key="presence_penalty",
        initial_value=0.4,
        default_value=0.4,
        description="主题重复惩罚",
    ),
    ConfigItem(
        key="text_filter",
        initial_value=[],
        default_value=[],
        description="回答过滤词，会以 * 呈现",
    ),
)


async def register_chat_agent_configs() -> None:
    await config_manager.add_configs(
        plugin_name="chat_agent", configs=CHAT_AGENT_CONFIGS
    )


@dataclass(slots=True)
class ChatAgentSettings:
    api_keys: list[str]
    api_base: str
    model: str
    temperature: float
    reply_max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    timeout: int
    memory_short_length: int
    memory_max_length: int
    reasoning_split: bool
    plugin_rerank_enabled: bool
    plugin_rerank_model: str
    plugin_rerank_top_n: int
    plugin_rerank_score_gap: float
    personality: str
    max_response_per_msg: int

    @classmethod
    def load(cls) -> "ChatAgentSettings":
        return cls(
            api_keys=sync_get_agent_config("api_keys", default_value=[]),
            api_base=sync_get_agent_config("api_base", default_value=""),
            model=sync_get_agent_config("model", default_value="gpt-3.5-turbo"),
            temperature=sync_get_agent_config("temperature", default_value=0.4),
            reply_max_tokens=sync_get_agent_config(
                "reply_max_tokens", default_value=1024
            ),
            top_p=sync_get_agent_config("top_p", default_value=1),
            frequency_penalty=sync_get_agent_config(
                "frequency_penalty", default_value=0.4
            ),
            presence_penalty=sync_get_agent_config(
                "presence_penalty", default_value=0.4
            ),
            timeout=sync_get_agent_config("timeout", default_value=60),
            memory_short_length=sync_get_agent_config(
                "memory_short_length", default_value=12
            ),
            memory_max_length=sync_get_agent_config(
                "memory_max_length", default_value=24
            ),
            reasoning_split=sync_get_agent_config(
                "reasoning_split", default_value=True
            ),
            plugin_rerank_enabled=sync_get_agent_config(
                "plugin_rerank_enabled", default_value=True
            ),
            plugin_rerank_model=sync_get_agent_config(
                "plugin_rerank_model", default_value=""
            ),
            plugin_rerank_top_n=sync_get_agent_config(
                "plugin_rerank_top_n", default_value=4
            ),
            plugin_rerank_score_gap=sync_get_agent_config(
                "plugin_rerank_score_gap", default_value=5.0
            ),
            personality=sync_get_agent_config(
                "personality", default_value="她叫{bot_name}，是一个搭配师"
            ),
            max_response_per_msg=sync_get_agent_config(
                "max_response_per_msg", default_value=5
            ),
        )
