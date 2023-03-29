from nonebot.adapters.onebot.v11 import MessageSegment
import aiohttp
from pathlib import Path
from typing import Tuple, Union
import datetime
from pil_utils import BuildImage

from migang.core import FONT_PATH
from PIL import ImageFont

banner_path = Path(__file__).parent / "image" / "webtop.png"


async def get_wbtop(url: str) -> Tuple[Union[dict, str], int]:
    """
    :param url: 请求链接
    """
    for i in range(3):
        try:
            data = []
            async with aiohttp.ClientSession() as client:
                get_response = await client.get(url, timeout=20)
                if get_response.status == 200:
                    data_json = (await get_response.json())["data"]["realtime"]
                    for data_item in data_json:
                        # 如果是广告，则不添加
                        if "is_ad" in data_item:
                            continue
                        dic = {
                            "hot_word": data_item["note"],
                            "hot_word_num": str(data_item["num"]),
                            "url": "https://s.weibo.com/weibo?q=%23"
                            + data_item["word"]
                            + "%23",
                        }
                        data.append(dic)
                    if not data:
                        return "没有搜索到...", 997
                    return {"data": data, "time": datetime.datetime.now()}, 200
                else:
                    if i > 2:
                        return f"获取失败,请十分钟后再试", 999
        except TimeoutError:
            return "超时了....", 998


def gen_wbtop_pic(data: dict) -> MessageSegment:
    """
    生成微博热搜图片
    :param data: 微博热搜数据
    """
    bk = BuildImage.new("RGBA", (700, 32 * 50 + 280), color="#797979")
    wbtop_bk = BuildImage.open(banner_path).resize((700, 280))
    bk.paste(wbtop_bk)
    text_bk = BuildImage.new("RGBA", (700, 32 * 50), color="#797979")
    ttf_font = ImageFont.truetype(
        str(FONT_PATH / "Yozai-Regular.ttf"), size=20, encoding="utf-8"
    )
    height = 0
    for i, data in enumerate(data):
        title = f"{i + 1}. {data['hot_word']}"
        hot = str(data["hot_word_num"])
        img = BuildImage.new("RGBA", (700, 30), color="white")
        _, h = ttf_font.getsize(title)
        img.draw_text((10, int((30 - h) / 2)), title, fontname="Yozai", fontsize=20)
        img.draw_text((580, int((30 - h) / 2)), hot, fontname="Yozai", fontsize=20)
        text_bk.paste(img, (0, height))
        height += img.height + 2
    bk.paste(text_bk, (0, 280))
    return MessageSegment.image(bk.save_png())
