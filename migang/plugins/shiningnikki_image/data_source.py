import aiohttp
from fake_useragent import UserAgent

from migang.core import DATA_PATH
from migang.utils.http import async_download_files
from migang.utils.file import async_load_data, async_save_data

DATA_PATH = DATA_PATH / "shiningnikki_image"
DATA_PATH.mkdir(exist_ok=True, parents=True)


async def update_suits_img():
    headers = {"user-agent": UserAgent(browsers=["chrome", "edge"]).random}
    async with aiohttp.ClientSession() as client:
        r = await client.head(
            "https://nikki4.papegames.cn/audiovisual?utm_source=official&utm_medium=home_nav",
            headers=headers,
            timeout=5,
        )
        cookie = r.cookies
        r = await client.get(
            "https://nikki4.papegames.cn/api/v1/picture",
            headers=headers,
            cookies=cookie,
            params={"limit": 0},
            timeout=5,
        )
        r = await client.get(
            "https://nikki4.papegames.cn/api/v1/picture",
            headers=headers,
            cookies=cookie,
            params={"limit": (await r.json())["total"]},
            timeout=5,
        )
        r = (await r.json())["data"]
    suits = await async_load_data(DATA_PATH / "suits.json")
    path = DATA_PATH / "suits"
    if not path.exists():
        path.mkdir(exist_ok=True, parents=True)
    img_set = set([img.name for img in path.iterdir()])
    insert_count = 0
    urls = []
    names = []
    for item in r:
        id_ = str(item["id"])
        if id_ not in suits:
            suits[id_] = {
                "url": item["content"],
                "name": item["title"].strip()
                if item["title"].strip()
                else "不愿意透露姓名的大裙子",
            }
            insert_count += 1
        if f"{id_}.jpg" not in img_set:
            urls.append(item["content"])
            names.append(f"{id_}.jpg")
    download_count = await async_download_files(
        urls=urls, path=path, names=names, stream=True, concurrency_limit=6
    )
    await async_save_data(suits, DATA_PATH / "suits.json")
    return insert_count, download_count
