import httpx
from thefuzz import fuzz
from typing import Tuple

url = "https://api.jikipedia.com/go/search_entities"
header = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
    "content-type": "application/json",
    "referer": "https://jikipedia.com/",
    "Client": "web",
    "Client-Version": "2.7.2d",
    "XID": "OLk5qKoDNfdUKFydz/lB6VFfmrl4IrGnfb/aCR5mzwOLxsqVWLgrPHE4V4zMkCPr2qexM57y5NM210aN67vGiSFMj0HkpGNyXHe6VTdrCzc=",
}


async def get_jiki(keyword: str) -> Tuple[str, str, str]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url=url,
            headers=header,
            json={"page": 1, "phrase": keyword, "size": 60},
            timeout=5,
        )
        result = resp.json()
    if "data" not in result:
        return "", "", ""
    title = None
    for item in result["data"]:
        if item["category"] != "definition":
            continue
        definitions = item["definitions"]
        if not definitions:
            continue
        definition = definitions[0]
        if fuzz.ratio(definition["term"]["title"].lower(), keyword.lower()) < 90:
            continue
        title = definition["term"]["title"]
        content = definition["plaintext"]
        img_urls = []
        for img in definition["images"]:
            img_urls.append(img["scaled"]["path"])
        break

    if not title:
        return "", "", ""
    msg = content
    if img_urls:
        msg += "<div>"
        for img in img_urls:
            msg += f'<img width="50%" src="{img}"/>'
        msg += "</div>"

    return title, msg, None
