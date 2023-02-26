import uuid
import random
import hashlib

import ujson
import aiohttp
from nonebot import get_driver

from migang.core import get_config

from .deepl_trans import DeeplTranslator
from .google_trans import GoogleTranslator


async def get_google_trans(text):
    try:
        return f"[谷歌机翻]\n> {await GoogleTranslator(source='auto', target='zh-CN').translate(text=text)}"
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
    headers["Ocp-Apim-Subscription-Key"] = await get_config("azure_api_key")


async def get_azure_trans(text):
    try:
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as client:
            r = await client.post(
                constructed_url, headers=headers, json=[{"text": text}]
            )
            return f"[微软机翻]\n> {(await r.json())[0]['translations'][0]['text']}"
    except:
        return "[微软机翻]\n> 出错了~"


async def get_baidu_trans(text):
    try:
        baidu_appid = await get_config("baidu_app_id")
        salt = random.randint(32768, 65536)
        sign = baidu_appid + text + str(salt) + (await get_config("baidu_api_key"))
        sign = hashlib.md5(sign.encode()).hexdigest()
        params = {
            "q": text,
            "from": "auto",
            "to": "zh",
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


async def get_deepl_trans(text):
    try:
        return f"[Deepl机翻]\n> {await DeeplTranslator(api_key=await get_config('deepl_api_key'),target='ZH',use_free_api=True,).translate(text)}"
    except:
        return "[Deepl机翻]\n> 出错了~"


url = f"http://fanyi.youdao.com/translate?smartresult=dict&smartresult=rule&smartresult=ugc&sessionFrom=null"


async def get_youdao_trans(text):
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
