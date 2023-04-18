import math
import uuid
import random
import hashlib
from typing import Dict

import ujson
import aiohttp
from nonebot import get_driver
from nonebot.log import logger
from nonebot.utils import run_sync
from deep_translator import DeeplTranslator, GoogleTranslator

from migang.core import get_config


def get_language_form(language: Dict[str, str], num_per_line: int = 5) -> str:
    language_list = list(language)
    lines = []
    lines.append("<div style='width:90'></div>".join(["|"] * (num_per_line + 1)))
    lines.append("|" + "|".join([":---"] * num_per_line) + "|")
    for i in range(math.ceil(len(language) / num_per_line)):
        this_line = []
        for j in range(num_per_line):
            if i * num_per_line + j >= len(language):
                this_line.append("")
            else:
                this_line.append(
                    f"**{language[language_list[i*num_per_line+j]]}：**{language_list[i*num_per_line+j]}"
                )
        lines.append("|" + "|".join(this_line) + "|")
    return "\n".join(lines)


google_language = {
    "af": "南非荷兰语",
    "sq": "阿尔巴尼亚",
    "am": "阿姆哈拉语",
    "ar": "阿拉伯",
    "hy": "亚美尼亚",
    "as": "阿萨姆语",
    "ay": "艾马拉",
    "az": "阿塞拜疆语",
    "bm": "穿",
    "eu": "巴斯克",
    "be": "白俄罗斯",
    "bn": "孟加拉",
    "bho": "博杰普里",
    "bs": "波斯尼亚",
    "bg": "保加利亚语",
    "ca": "加泰罗尼亚语",
    "ceb": "宿雾语",
    "ny": "奇切瓦",
    "zh-CN": "简体中文",
    "zh-TW": "繁体中文",
    "co": "科西嘉",
    "hr": "克罗地亚语",
    "cs": "捷克语",
    "da": "丹麦语",
    "dv": "迪维希语",
    "doi": "多格里",
    "nl": "荷兰语",
    "lg": "英语",
    "eo": "世界语",
    "et": "爱沙尼亚语",
    "ee": "母羊",
    "tl": "菲律宾人",
    "fi": "芬兰",
    "fr": "法语",
    "fy": "弗里斯兰语",
    "gl": "加利西亚语",
    "ka": "格鲁吉亚语",
    "de": "德语",
    "el": "希腊语",
    "gn": "瓜拉尼语",
    "gu": "古吉拉特语",
    "ht": "海地克里奥尔语",
    "ha": "豪萨语",
    "haw": "夏威夷",
    "iw": "希伯来语",
    "hi": "印地语",
    "hmn": "苗族",
    "hu": "匈牙利",
    "is": "冰岛的",
    "ig": "伊博语",
    "ilo": "伊洛卡诺",
    "id": "印度尼西亚",
    "ga": "爱尔兰的",
    "it": "意大利语",
    "ja": "日本人",
    "jw": "爪哇语",
    "kn": "卡纳达语",
    "kk": "哈萨克语",
    "km": "高棉语",
    "rw": "基尼亚卢旺达语",
    "gom": "孔卡尼",
    "ko": "韩国人",
    "kri": "隐藏",
    "ku": "库尔德",
    "ckb": "库尔德（索拉尼）",
    "ky": "吉尔吉斯语",
    "lo": "老挝",
    "la": "拉丁",
    "lv": "拉脱维亚语",
    "ln": "林加拉语",
    "lt": "立陶宛语",
    "lb": "卢森堡语",
    "mk": "马其顿语",
    "mai": "迈蒂利",
    "mg": "马尔加什",
    "ms": "马来语",
    "ml": "马拉雅拉姆语",
    "mt": "马耳他语",
    "mi": "毛利人",
    "mr": "马拉地语",
    "mni-Mtei": "美特隆",
    "lus": "沟沟",
    "mn": "蒙",
    "my": "缅甸",
    "ne": "尼泊尔语",
    "no": "挪 威",
    "or": "奥里亚语",
    "om": "奥罗莫",
    "ps": "普什图语",
    "fa": "波斯语",
    "pl": "抛光",
    "pt": "葡萄牙语",
    "pa": "旁遮普语",
    "qu": "克丘亚语",
    "ro": "罗马尼亚语",
    "ru": " 俄语",
    "sm": "萨摩亚语",
    "sa": "梵文",
    "gd": "苏格兰盖尔语",
    "nso": "塞佩迪",
    "sr": "塞尔维亚",
    "st": "塞索托语",
    "sn": "绍纳",
    "sd": "信德",
    "si": "僧伽罗语",
    "sk": "斯 洛伐克语",
    "sl": "斯洛文尼亚语",
    "so": "索马里",
    "es": "西班牙语",
    "su": "巽他语",
    "sw": "斯瓦希里语",
    "sv": "瑞典",
    "tg": "塔吉克",
    "ta": "泰米尔语",
    "tt": "鞑靼人",
    "te": "泰卢固语",
    "th": "泰国",
    "ti": "提格里尼亚语",
    "ts": "特松加",
    "tr": "土耳其",
    "tk": "土库曼人",
    "ak": "双胞胎",
    "uk": "乌克兰",
    "ur": "乌尔都语",
    "ug": "维吾尔人",
    "uz": "乌兹别克语",
    "vi": "越南语",
    "cy": "威尔士语",
    "xh": "科萨语",
    "yi": "意第绪语",
    "yo": "约鲁巴语",
    "zu": "祖鲁语",
}


@run_sync
def get_google_trans(text: str, to: str = "zh-CN"):
    if to not in google_language:
        return f"[谷歌机翻]\n> 目标语言不受支持..."
    try:
        return f"[谷歌机翻]\n> {GoogleTranslator(source='auto', target=to).translate(text=text)}"
    except:
        return "[谷歌机翻]\n> 出错了~"


region = "global"
base_url = "https://api.cognitive.microsofttranslator.com/"
path = "/translate?api-version=3.0"
params = "&to=zh"
constructed_url = base_url + path + params
headers = {
    "Ocp-Apim-Subscription-Region": region,
    "Content-type": "application/json",
    "X-ClientTraceId": str(uuid.uuid4()),
}


@get_driver().on_startup
async def _():
    global headers
    try:
        headers["Ocp-Apim-Subscription-Key"] = await get_config("azure_api_key")
    except Exception:
        logger.warning("首次启动，请填写azure_api_key")


async def get_azure_trans(text: str):
    try:
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as client:
            r = await client.post(
                constructed_url, headers=headers, json=[{"text": text}]
            )
            return f"[微软机翻]\n> {(await r.json())[0]['translations'][0]['text']}"
    except:
        return "[微软机翻]\n> 出错了~"


baidu_language = {
    "yue": "粤语",
    "kor": "韩语",
    "th": "泰语",
    "pt": "葡萄牙语",
    "el": "希腊语",
    "bul": "保加利亚语",
    "fin": "芬兰语",
    "slo": "斯洛文尼亚语",
    "cht": "繁体中文",
    "zh": "中文",
    "wyw": "文言文",
    "fra": "法语",
    "ara": "阿拉伯语",
    "de": "德语",
    "nl": "荷兰语",
    "est": "爱沙尼亚语",
    "cs": "捷克语",
    "swe": "瑞典语",
    "vie": "越南语",
    "en": "英语",
    "jp": "日语",
    "spa": "西班牙语",
    "ru": "俄语",
    "it": "意大利语",
    "pl": "波兰语",
    "dan": "丹麦语",
    "rom": "罗马尼亚语",
    "hu": "匈牙利语",
}


async def get_baidu_trans(text: str, to: str = "zh"):
    if to not in baidu_language:
        return "[百度机翻]\n> 目标语言不受支持..."
    try:
        baidu_appid = await get_config("baidu_app_id")
        salt = random.randint(32768, 65536)
        sign = baidu_appid + text + str(salt) + (await get_config("baidu_api_key"))
        sign = hashlib.md5(sign.encode()).hexdigest()
        params = {
            "q": text,
            "from": "auto",
            "to": to,
            "appid": baidu_appid,
            "salt": salt,
            "sign": sign,
        }
        async with aiohttp.ClientSession() as client:
            r = await client.get(
                "https://api.fanyi.baidu.com/api/trans/vip/translate",
                params=params,
                timeout=10,
            )
            return f"[百度机翻]\n> {(await r.json())['trans_result'][0]['dst']}"
    except:
        return "[百度机翻]\n> 出错了~"


@run_sync
async def get_deepl_trans(text: str):
    try:
        return f"[Deepl机翻]\n> {DeeplTranslator(api_key=await get_config('deepl_api_key'),target='ZH',use_free_api=True,).translate(text)}"
    except:
        return "[Deepl机翻]\n> 出错了~"


url = "http://fanyi.youdao.com/translate?smartresult=dict&smartresult=rule&smartresult=ugc&sessionFrom=null"


async def get_youdao_trans(text: str):
    data = {
        "type": "EN2ZH_CN",
        "i": text,
        "doctype": "json",
        "version": "2.1",
        "keyfrom": "fanyi.web",
        "ue": "UTF-8",
        "action": "FY_BY_CLICKBUTTON",
        "typoResult": "true",
    }
    try:
        async with aiohttp.ClientSession() as client:
            data = await (await client.post(url, data=data)).json()
        if data["errorCode"] == 0:
            return f"[有道机翻]\n> {data['translateResult'][0][0]['tgt']}"
        else:
            return "[有道机翻]\n> 出错了~"
    except:
        return "[有道机翻]\n> 出错了~"
