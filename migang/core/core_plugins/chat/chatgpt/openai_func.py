from typing import Dict, List, Tuple, Optional

from nonebot.log import logger
from tenacity import retry, retry_if_exception, stop_after_attempt

from migang.core import sync_get_config

from .asyncopenai import async_openai


class RetryGetResponse(Exception):
    """重试获取回复"""

    def __init__(self, error_info):
        super().__init__(self)
        self.error_info_ = error_info

    def __str__(self):
        return self.error_info_


class TextGenerator:
    def __init__(
        self,
        api_keys: List[str],
        api_base: str,
        proxy: str,
        model: str,
        temperature: float,
        max_tokens: int,
        top_p: int,
        frequency_penalty: float,
        presence_penalty: float,
        timeout: int,
        max_impression_tokens: int,
    ) -> None:
        # openai异步
        self.__openai = async_openai
        self.__api_keys = api_keys
        self.__key_index = 0
        if proxy:
            if not proxy.startswith("http"):
                proxy = "http://" + proxy
            self.__openai.proxy = proxy
        if api_base != None and api_base.strip() != "":
            self.__openai.base_url = api_base
        # config
        self.__model = model
        self.__temperature = temperature
        self.__max_tokens = max_tokens
        self.__top_p = top_p
        self.__frequency_penalty = frequency_penalty
        self.__presence_penalty = presence_penalty
        self.__timeout = timeout
        self.__max_impression_tokens = max_impression_tokens

    # 获取文本生成
    @retry(stop=stop_after_attempt(3), retry=retry_if_exception(RetryGetResponse))
    async def get_response(
        self, prompt, type_: str = "chat", custom: Optional[Dict] = None
    ) -> Tuple[str, bool]:
        # return 'testing...'
        for _ in range(len(self.__api_keys)):
            if type_ == "chat":
                res, success = await self.get_chat_response(
                    self.__api_keys[self.__key_index], prompt, custom
                )
            elif type_ == "impression":
                res, success = await self.get_impression_response(
                    self.__api_keys[self.__key_index], prompt
                )
            if success:
                return res, True
            print("================")
            print(res)
            # 请求错误处理
            if "Rate limit" in res:
                reason = res
                res = "超过每分钟请求次数限制，喝杯茶休息一下吧 (´；ω；`)"
            elif "module 'openai' has no attribute 'ChatCompletion'" in res:
                reason = res
                res = "当前 openai 库版本过低，无法使用 gpt-3.5-turbo 模型 (´；ω；`)"
                break
            elif "Error communicating with OpenAI" in res:
                reason = res
                res = "与 OpenAi 通信时发生错误 (´；ω；`)"
            elif "retry your request" in res:
                raise RetryGetResponse("模型过载，重新尝试获取回复")
            else:
                reason = res
                res = "哎呀，发生了未知错误 (´；ω；`)"
            self.__key_index = (self.__key_index + 1) % len(self.__api_keys)
            logger.warning(
                f"当前 Api Key({self.__key_index}): [{self.__api_keys[self.__key_index][:4]}...{self.__api_keys[self.__key_index][-4:]}] 请求错误，尝试使用下一个...\n错误原因: {res} => {reason}"
            )
        logger.error("请求 OpenAi 发生错误，请检查 Api Key 是否正确或者查看控制台相关日志")
        return res, False

    # 对话文本生成
    async def get_chat_response(self, key: str, prompt: List | str, custom: Dict):
        self.__openai.api_key = key
        try:
            response = await self.__openai.chat.completions.create(
                model=self.__model,
                messages=prompt
                if isinstance(prompt, List)
                else [  # 如果是列表则直接使用，否则按照以下格式转换
                    {
                        "role": "system",
                        "content": f"You must strictly follow the user's instructions to give {custom.get('bot_name', 'bot')}'s response.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.__temperature,
                max_tokens=self.__max_tokens,
                top_p=self.__top_p,
                frequency_penalty=self.__frequency_penalty,
                presence_penalty=self.__presence_penalty,
                timeout=self.__timeout,
                stop=[
                    f"\n{custom.get('bot_name', 'AI')}:",
                    f"\n{custom.get('sender_name', 'Human')}:",
                ],
            )
            res = ""
            for choice in response.choices:
                res += choice.message.content
            res = res.strip()
            # 去掉头尾引号（如果有）
            if res.startswith('"') and res.endswith('"'):
                res = res[1:-1]
            if res.startswith("'") and res.endswith("'"):
                res = res[1:-1]
            # 去掉可能存在的开头起始标志
            if res.startswith(f"{custom.get('bot_name', 'AI')}:"):
                res = res[len(f"{custom.get('bot_name', 'AI')}:") :]
            # 去掉可能存在的开头起始标志 (中文)
            if res.startswith(f"{custom.get('bot_name', 'AI')}："):
                res = res[len(f"{custom.get('bot_name', 'AI')}：") :]
            # 替换多段回应中的回复起始标志
            res = res.replace(f"\n\n{custom.get('bot_name', 'AI')}:", "*;")
            return res, True
        except Exception as e:
            return f"请求 OpenAi Api 时发生错误: {e}", False

    # 印象文本生成
    async def get_impression_response(self, key: str, prompt: str):
        self.__openai.api_key = key
        try:
            response = await self.__openai.chat.completions.create(
                model=self.__model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=0.6,
                max_tokens=self.__max_impression_tokens,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                timeout=self.__timeout,
            )
            res = ""
            for choice in response.choices:
                res += choice.message.content
            res = res.strip()
            # 去掉头尾引号（如果有）
            if res.startswith('"') and res.endswith('"'):
                res = res[1:-1]
            if res.startswith("'") and res.endswith("'"):
                res = res[1:-1]
            return res, True
        except Exception as e:
            return f"请求 OpenAi Api 时发生错误: {e}", False


text_generator: TextGenerator = TextGenerator(
    api_keys=sync_get_config("api_keys", "chat_chatgpt"),
    api_base=sync_get_config("api_base", "chat_chatgpt"),
    proxy=sync_get_config("proxy", "chat_chatgpt"),
    model=sync_get_config("model", plugin_name="chat_chatgpt"),
    temperature=sync_get_config("temperature", plugin_name="chat_chatgpt"),
    max_tokens=sync_get_config("reply_max_tokens", plugin_name="chat_chatgpt"),
    top_p=sync_get_config("top_p", plugin_name="chat_chatgpt"),
    frequency_penalty=sync_get_config("frequency_penalty", plugin_name="chat_chatgpt"),
    presence_penalty=sync_get_config("presence_penalty", plugin_name="chat_chatgpt"),
    timeout=sync_get_config("timeout", plugin_name="chat_chatgpt"),
    max_impression_tokens=sync_get_config(
        "max_impression_tokens", plugin_name="chat_chatgpt"
    ),
)
