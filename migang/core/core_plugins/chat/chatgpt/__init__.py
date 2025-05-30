from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from migang.core.manager import config_manager
from migang.core import ConfigItem, pre_init_manager

from ..exception import BreakSession
from .chat import do_chat, pre_check


@pre_init_manager
async def _():
    await config_manager.add_configs(
        plugin_name="chat_chatgpt",
        configs=(
            ConfigItem(
                key="personality",
                default_value="她叫{bot_name}，是一个搭配师",
                description="chatgpt人格预设",
            ),
            ConfigItem(key="api_base", description="若使用第三方openai api，填写这个"),
            ConfigItem(
                key="api_keys",
                initial_value=[],
                default_value=[],
                description="openai的apikey",
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
                key="impression_length",
                initial_value=20,
                default_value=20,
                description="生成印象需要的会话长度",
            ),
            ConfigItem(
                key="impression_refresh_length",
                initial_value=10,
                default_value=10,
                description="每n条消息刷新一次印象",
            ),
            ConfigItem(
                key="timeout",
                initial_value=60,
                default_value=60,
                description="openai请求超时时间",
            ),
            ConfigItem(
                key="ignore_prefix", initial_value=["/"], description="以此前缀为开头的消息不被处理"
            ),
            ConfigItem(
                key="max_response_per_msg",
                initial_value=5,
                default_value=5,
                description="每条消息最大响应次数",
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
                description="单次回复最大token数",
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
                "max_impression_tokens",
                initial_value=512,
                default_value=512,
                description="单次印象最大token",
            ),
            ConfigItem(
                "unlock_content",
                initial_value=False,
                default_value=False,
                description="解锁内容限制",
            ),
            ConfigItem("proxy", description="代理服务器"),
            ConfigItem(
                "embedding_model",
                description="embedding模型",
                default_value="",
                initial_value="",
            ),
        ),
    )


from .tools import *
from .plugin_vector_db import *
from .langchain_tools import tool_manager  # noqa

# ========================= #
# langchain实现
from .langchain_chat import langchain_chatbot  # noqa

# ========================= #


async def get_gpt_chat(matcher: Matcher, event: GroupMessageEvent, bot: Bot):
    state = {}
    if await pre_check(event=event, bot=bot, state=state):
        await do_chat(matcher=matcher, event=event, bot=bot, state=state)
    raise BreakSession("由naturel_gpt处理发送逻辑")


async def not_at_rule(bot: Bot, event: GroupMessageEvent, state: T_State) -> bool:
    # 只响应非at事件，at事件让别的去管
    if event.is_tome():
        return False

    return await pre_check(event=event, bot=bot, state=state)
