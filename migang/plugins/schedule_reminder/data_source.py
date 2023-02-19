import re
from datetime import datetime, timedelta

import httpx
from croniter import croniter
from nonebot import get_driver
from nonebot.log import logger

api_url = "sm.sm"


@get_driver().on_startup
async def _():
    global api_url
    try:
        async with httpx.AsyncClient() as client:
            await client.head(f"https://{api_url}/api/v2/upload")
    except Exception:
        logger.debug(f"已切换到 smms.app")
        api_url = "smms.app"


async def upload_image(img_url, token=""):
    headers = {}
    if token:
        headers = {"Authorization": token}
    try:
        async with httpx.AsyncClient() as client:
            original_image = await client.get(url=img_url, timeout=5)
            sm_req = await client.post(
                headers=headers,
                url=f"https://{api_url}/api/v2/upload",
                files={"smfile": original_image.content},
                timeout=30,
            )
        return sm_req.json()
    except Exception as e:
        logger.warning(f"上传 {img_url} 失败：{e}")
        return None


CQ_PATTERN = r"\[CQ:\w+,.+?\]"
IMAGE_PATTERN = r"\[CQ:(?:image),.*(?:url|file)=(https?://.*)\]"
IMAGE_URL_PATTERN = r"https?://.*\.(?:jpg|png|gif|webp|jpeg|jfif)"


def get_image_url(CQ_text):
    urls = re.findall(IMAGE_URL_PATTERN, CQ_text)
    return urls


def get_CQ_image(CQ_text):
    cqs = re.findall(CQ_PATTERN, CQ_text)
    imgs = {}
    for i in cqs:
        img = re.findall(IMAGE_PATTERN, i)
        if img:
            imgs[img[0]] = i
    return imgs


MONTHDAY = {
    "1": 31,
    "2": 28,
    "3": 31,
    "4": 30,
    "5": 31,
    "6": 30,
    "7": 31,
    "8": 31,
    "9": 30,
    "10": 31,
    "11": 30,
    "12": 31,
}


def cronParse(cron):
    if not croniter.is_valid(cron):
        return False, None, None, None
    time = datetime.now()
    iter = croniter(cron, time)
    return (
        True,
        iter.get_next(datetime),
        iter.get_next(datetime),
        iter.get_next(datetime),
    )


def dateParse(time):
    mode = 0
    if time.endswith("后"):
        mode = 1
    if mode == 0:
        year = re.search(r"[\d+]+年", time)
        month = re.search(r"[\d+]+月", time)
        r = re.search(r"[\d+]+[日|号]", time)
        hour = re.search(r"[\d+]+[点|时]", time)
        min = re.search(r"[\d+]+分", time)
        if month:
            timeNow = datetime.now()
            y = timeNow.year
            m = int(month.group().rstrip("月"))
            ri = 1
            if r:
                ri = int(r.group().rstrip("日").rstrip("号"))
            if year:
                y = int(year.group().rstrip("年"))
            # check month and day
            if m < 1 or m > 12 or ri < 1 or ri > 31:
                return False, None
            if m == 2 and ((y % 4 == 0 and y % 100 != 0) or y % 400 == 0):
                if ri > MONTHDAY[str(m)] + 1:
                    return False, None
            elif ri > MONTHDAY[str(m)]:
                return False, None

            if hour:
                h = int(hour.group().rstrip("点").rstrip("时"))
            else:
                h = 0

            if min:
                mi = int(min.group().rstrip("分"))
            else:
                mi = 0

            return True, datetime(y, m, ri, h, mi)
        else:
            dayDiff = 0
            if "明天" in time:
                dayDiff = 1
            elif "后天" in time:
                dayDiff = 2
            else:
                day = re.search(r"[\d+]+天后", time)
                if day:
                    dayDiff = int(day.group.rstrip("天后"))
            now = datetime.now()
            timeBase = now + timedelta(days=dayDiff)
            if hour:
                h = int(hour.group().rstrip("点").rstrip("时"))
                if h < 0 or h > 24:
                    return False, None
                timeBase = timeBase.replace(hour=h)
                timeBase = timeBase.replace(minute=0)
            if min:
                m = int(min.group().rstrip("分"))
                if m < 0 or m > 60:
                    return False, None
                timeBase = timeBase.replace(minute=m)
            if timeBase == now:
                return False, None
            return True, timeBase
    elif mode == 1:
        day = re.search(r"[\d+]+[天|日]", time)
        hour = re.search(r"[\d+]+[时|小时]", time)
        min = re.search(r"[\d+]+[分|分钟]", time)
        dayDiff = 0
        hourDiff = 0
        minDiff = 0
        if day:
            dayDiff = int(day.group().rstrip("天").rstrip("日"))
        if hour:
            hourDiff = int(hour.group().rstrip("时").rstrip("小时"))
        if min:
            minDiff = int(min.group().rstrip("分").rstrip("分钟"))
        timeBase = datetime.now() + timedelta(
            days=dayDiff, hours=hourDiff, minutes=minDiff
        )

        return True, timeBase


def intervalParse(interval):
    # m : minites, d: day, h:hour
    inSettings = interval.split(":")
    if len(inSettings) != 2:
        return False, "参数个数错误，参考[m:分钟，d:天数，h:小时数]发送", None
    if inSettings[0] == "m":
        return True, "m", int(inSettings[1])
    elif inSettings[0] == "d":
        return True, "d", int(inSettings[1])
    elif inSettings[0] == "h":
        return True, "h", int(inSettings[1])
    else:
        return False, "类型错误，仅支持[m:分钟，d:天数，h:小时数]", None
