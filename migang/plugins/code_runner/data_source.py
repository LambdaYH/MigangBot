import re
import math
from typing import Union

import ujson
import aiohttp
from nonebot import require
from nonebot.adapters.onebot.v11 import MessageSegment

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import md_to_pic, text_to_pic

RUN_API_URL_FORMAT = "https://glot.io/run/{}?version=latest"
SUPPORTED_LANGUAGES = {
    "assembly": {"ext": "asm"},
    "bash": {"ext": "sh"},
    "c": {"ext": "c"},
    "clojure": {"ext": "clj"},
    "coffeescript": {"ext": "coffe"},
    "cpp": {"ext": "cpp"},
    "csharp": {"ext": "cs"},
    "erlang": {"ext": "erl"},
    "fsharp": {"ext": "fs"},
    "go": {"ext": "go"},
    "groovy": {"ext": "groovy"},
    "haskell": {"ext": "hs"},
    "java": {"ext": "java", "name": "Main"},
    "javascript": {"ext": "js"},
    "julia": {"ext": "jl"},
    "kotlin": {"ext": "kt"},
    "lua": {"ext": "lua"},
    "perl": {"ext": "pl"},
    "php": {"ext": "php"},
    "python": {"ext": "py"},
    "ruby": {"ext": "rb"},
    "rust": {"ext": "rs"},
    "scala": {"ext": "scala"},
    "swift": {"ext": "swift"},
    "typescript": {"ext": "ts"},
}


def list_supp_lang(split_num: int = None) -> str:
    if not split_num:
        return "/".join(SUPPORTED_LANGUAGES.keys())
    ret = []
    support_languages_list = list(SUPPORTED_LANGUAGES.keys())
    for i in range(math.ceil(len(support_languages_list) / split_num)):
        ret.append(
            "/".join(support_languages_list[i * split_num : (i + 1) * split_num])
        )
    return "\n".join(ret)


async def runner(msg: str) -> Union[str, MessageSegment]:
    args = re.split(r"[\n| ]", msg, maxsplit=1)
    if len(args) != 2:
        return "请检查键入内容..."

    lang = args[0].replace("\r", "")
    if lang not in SUPPORTED_LANGUAGES:
        return MessageSegment.image(
            await text_to_pic(f"该语言暂不支持...或者可能格式错误？\n支持的语言：\n{list_supp_lang(7)}")
        )

    code = args[1].strip().strip("\n")
    print(code)
    url = RUN_API_URL_FORMAT.format(lang)
    js = {
        "files": [
            {
                "name": (
                    SUPPORTED_LANGUAGES[lang].get("name", "main")
                    + f".{SUPPORTED_LANGUAGES[lang]['ext']}"
                ),
                "content": code,
            }
        ],
        "stdin": "",
        "command": "",
    }
    async with aiohttp.ClientSession(json_serialize=ujson.dumps) as client:
        try:
            res = await client.post(url, json=js)
        except Exception as e:
            return f"请求错误：{e}"
        payload = await res.json()
    if stdout := payload.get("stdout"):
        return MessageSegment.image(await md_to_pic(stdout))
    elif stderr := payload.get("stderr"):
        return MessageSegment.image(await text_to_pic(stderr))
    elif error := payload.get("error"):
        return MessageSegment.image(await text_to_pic(error))

    return "运行完成，没任何输出呢..."
