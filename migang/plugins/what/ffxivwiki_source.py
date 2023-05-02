import re
from typing import List, Tuple

import aiohttp
from nonebot.log import logger

GARLAND = "https://ffxiv.cyanclay.xyz"

CAFEMAKER = "https://cafemaker.wakingsands.com"
XIVAPI = "https://xivapi.com"

XIV_TAG_REGEX = re.compile(r"<(.*?)>")
GT_CORE_DATA_CN = None
GT_CORE_DATA_GLOBAL = None
NODE_NAME_BY_TYPE = {0: "矿脉", 1: "石场", 2: "良材", 3: "草场", 4: "鱼影", 5: "鱼影"}

FISH_SHADOW_SIZE = {"S": "小型", "M": "中型", "L": "大型", "Map": "宝藏地图"}

FISH_SHADOW_SPEED = {
    "Slow": "慢",
    "Average": "中速",
    "Fast": "快",
    "Very Fast": "非常快",
    "V. Fast": "非常快",
}


# use garlandtools.cn if your server is in China
# else use ffxiv.cyanclay.xyz, which located at German
def craft_garland_url(item_category, item_id, name_lang):
    is_cn = name_lang == "chs"
    return f"{GARLAND if is_cn else 'https://garlandtools.org'}/db/doc/{item_category}/{name_lang}/3/{item_id}.json"


def parse_xiv_html(string):
    def handle_tag(tag_match):
        tag = tag_match.group(1)
        return "\n" if tag == "br" else ""

    return XIV_TAG_REGEX.sub(handle_tag, string)


async def gt_core(key: str, lang: str):
    global GT_CORE_DATA_CN, GT_CORE_DATA_GLOBAL
    if lang == "chs":
        if GT_CORE_DATA_CN is None:
            async with aiohttp.ClientSession() as client:
                GT_CORE_DATA_CN = await client.get(
                    craft_garland_url("core", "data", "chs"), timeout=3
                )
                GT_CORE_DATA_CN = await GT_CORE_DATA_CN.json(content_type=None)
        GT_CORE_DATA = GT_CORE_DATA_CN
    else:
        if GT_CORE_DATA_GLOBAL is None:
            async with aiohttp.ClientSession() as client:
                GT_CORE_DATA_GLOBAL = await client.get(
                    craft_garland_url("core", "data", "en"), timeout=3
                )
                GT_CORE_DATA_GLOBAL = await GT_CORE_DATA_GLOBAL.json(content_type=None)
        GT_CORE_DATA = GT_CORE_DATA_GLOBAL
    req = GT_CORE_DATA
    for par in key.split("."):
        req = req[par]
    return req


async def parse_item_garland(item_id, name_lang):
    if name_lang == "cn":
        name_lang = "chs"
    img_urls = []

    async with aiohttp.ClientSession() as client:
        j = await client.get(craft_garland_url("item", item_id, name_lang), timeout=3)
        j = await j.json(content_type=None)

    result = []
    # index partials
    partials = {}
    for p in j["partials"] if "partials" in j.keys() else []:
        partials[(p["type"], p["id"])] = p["obj"]

    item = j["item"]
    # start processing
    if "icon" in item.keys():
        image_url = f"{GARLAND}/files/icons/item/{item['icon'] if str(item['icon']).startswith('t/') else 't/' + str(item['icon'])}.png"
        img_urls.append(image_url)

    result.append(item["name"])
    result.append(
        await gt_core(f"item.categoryIndex.{item['category']}.name", name_lang)
    )
    result.append(f"物品等级 {item['ilvl']}")
    if "equip" in item.keys():
        result.append(f"装备等级 {item['elvl']}")

    if "jobCategories" in item.keys():
        result.append(item["jobCategories"])

    if "description" in item.keys():
        result.append(parse_xiv_html(item["description"]))

    hasSource = False

    def format_limit_time(times):
        limitTimes = "\n艾欧泽亚时间 "
        for time in times:
            limitTimes += f"{time}时 "
        limitTimes += "开放采集"
        return limitTimes

    if "nodes" in item.keys():
        hasSource = True
        result.append("·采集")
        for nodeIndex in item["nodes"]:
            node = partials[("node", str(nodeIndex))]
            result.append(
                "  -- {} {} {} {}{}".format(
                    await gt_core(f"locationIndex.{node['z']}.name", name_lang),
                    node["n"],
                    "{}{}".format(
                        "" if "lt" not in node.keys() else node["lt"],
                        NODE_NAME_BY_TYPE[int(node["t"])],
                    ),
                    f"({node['c'][0]}, {node['c'][1]})",
                    "" if "ti" not in node.keys() else format_limit_time(node["ti"]),
                )
            )
        result.append("")

    if "fishingSpots" in item.keys():
        hasSource = True
        result.append("·钓鱼")
        for spotIndex in item["fishingSpots"]:
            spot = partials[("fishing", str(spotIndex))]
            result.append(
                "  -- {} {} {} {}".format(
                    await gt_core(f"locationIndex.{spot['z']}.name", name_lang),
                    spot["n"],
                    f"{spot['c']} {spot['l']}级",
                    "" if "x" not in spot.keys() else f"({spot['x']}, {spot['y']})",
                )
            )
        result.append("")

    if "fish" in item.keys():
        result.append("·钓法/刺鱼指引")
        for fishGroup in item["fish"]["spots"]:
            if "spot" in fishGroup.keys():
                result.append(f"  {fishGroup['hookset']} {fishGroup['tug']}")
                if "predator" in fishGroup.keys():
                    result.append("- 需求捕鱼人之识")
                    for predator in fishGroup["predator"]:
                        result.append(
                            "  - {} *{}".format(
                                partials[("item", str(predator["id"]))]["n"],
                                predator["amount"],
                            )
                        )
                if "baits" in fishGroup.keys():
                    result.append("- 可用鱼饵")
                    for baitChains in fishGroup["baits"]:
                        chain = ""
                        for bait in baitChains:
                            if not len(chain) == 0:
                                chain += " -> "
                            chain += partials[("item", str(bait))]["n"]
                        result.append(f"  - {chain}")
                if "during" in fishGroup.keys():
                    result.append(
                        f"- 限ET {fishGroup['during']['start']}时至{fishGroup['during']['end']}时"
                    )
                if "weather" in fishGroup.keys():
                    w = " ".join(fishGroup["weather"])
                    if "transition" in fishGroup.keys():
                        w = w + " -> " + " ".join(fishGroup["transition"])
                    result.append(f"- 限{w}")
            elif "node" in fishGroup.keys():
                result.append(f"- 鱼影大小 {FISH_SHADOW_SIZE[fishGroup['shadow']]}")
                result.append(f"- 鱼影速度 {FISH_SHADOW_SPEED[fishGroup['speed']]}")
        result.append("")

    if "reducedFrom" in item.keys():
        hasSource = True
        result.append("·精选")
        for itemIndex in item["reducedFrom"]:
            result.append("- {}".format(partials[("item", str(itemIndex))]["n"]))
        result.append("")

    if "craft" in item.keys():
        hasSource = True
        result.append("·制作")
        for craft in item["craft"]:
            result.append(
                "  -- {} {}".format(
                    await gt_core("jobs", name_lang)[craft["job"]]["name"],
                    f"{craft['lvl']}级",
                )
            )
            result.append("  材料:")
            for ingredient in craft["ingredients"]:
                if ingredient["id"] < 20:
                    continue
                result.append(
                    "   - {} {}个".format(
                        partials[("item", str(ingredient["id"]))]["n"],
                        ingredient["amount"],
                    )
                )
        result.append("")

    if "vendors" in item.keys():
        hasSource = True
        result.append(f"·商店贩售 {item['price']}金币")
        i = 0
        for vendor in item["vendors"]:
            if i > 4:
                result.append(f"等共计{len(item['vendors'])}个商人售卖")
                break
            vendor_partial = partials["npc", str(vendor)]
            result.append(
                "  -- {} {} {}".format(
                    vendor_partial["n"],
                    await gt_core(
                        f"locationIndex.{vendor_partial['l']}.name", name_lang
                    )
                    if "l" in vendor_partial.keys()
                    else "",
                    f"({vendor_partial['c'][0]}, {vendor_partial['c'][1]})"
                    if "c" in vendor_partial.keys()
                    else "",
                )
            )
            i += 1
        pass

    if "tradeCurrency" in item.keys() or "tradeShops" in item.keys():
        hasSource = True
        tradeCurrency = []
        tradeShops = []
        try:
            tradeCurrency = item["tradeCurrency"]
        except KeyError:
            # ignore
            pass
        try:
            tradeShops = item["tradeShops"]
        except KeyError:
            # ignore
            pass
        trades = tradeCurrency + tradeShops
        i = 0
        for trade in trades:
            if i > 4:
                result.append(f"等共计{len(trades)}种购买方式")
                break

            shop_name = trade["shop"]
            result.append(
                "·{}".format(
                    "商店交易" if shop_name == "Shop" else shop_name,
                )
            )

            j = 0
            for vendor in trade["npcs"]:
                if j > 2:
                    result.append(f"等共计{len(trade['npcs'])}个商人交易")
                    break
                vendor_partial = partials["npc", str(vendor)]
                result.append(
                    "  -- {} {} {}".format(
                        vendor_partial["n"],
                        await gt_core(
                            f"locationIndex.{vendor_partial['l']}.name", name_lang
                        )
                        if "l" in vendor_partial.keys()
                        else "",
                        f"({vendor_partial['c'][0]}, {vendor_partial['c'][1]})"
                        if "c" in vendor_partial.keys()
                        else "",
                    )
                )
                j += 1
            j = 0
            for listing in trade["listings"]:
                if j > 2:
                    result.append(f"等共计{len(trade['listings'])}种兑换方式")
                    break
                listing_str = ""
                currency_str = ""
                k = 0
                for listingItem in listing["item"]:
                    if k > 2:
                        result.append(f"等共计{len(listing['item'])}项商品兑换")
                        break
                    listing_str += "- {}{} *{}\n".format(
                        item["name"]
                        if str(listingItem["id"]) == str(item_id)
                        else partials[("item", str(listingItem["id"]))]["n"],
                        "HQ" if "hq" in listingItem.keys() else "",
                        listingItem["amount"],
                    )
                    k += 1
                k = 0
                for currency in listing["currency"]:
                    if k > 2:
                        result.append(f"等共计{len(listing['currency'])}项商品兑换")
                        break
                    currency_str += "- {}{} *{}\n".format(
                        item["name"]
                        if str(currency["id"]) == str(item_id)
                        else partials[("item", str(currency["id"]))]["n"],
                        "HQ" if "hq" in currency.keys() else "",
                        currency["amount"],
                    )
                result.append("使用\n{}兑换获得\n{}".format(currency_str, listing_str))

    if "drops" in item.keys():
        hasSource = True
        result.append("·怪物掉落")
        for mobIndex in item["drops"]:
            mob = partials[("mob", str(mobIndex))]
            result.append(
                "  -- {} {}".format(
                    mob["n"], await gt_core(f"locationIndex.{mob['z']}.name", name_lang)
                )
            )
        result.append("")

    if "instances" in item.keys():
        hasSource = True
        result.append("·副本获取")
        i = 0
        for dutyIndex in item["instances"]:
            if i > 4:
                result.append(f"等共计{len(item['instances'])}个副本获取")
                break
            duty = partials[("instance", str(dutyIndex))]
            result.append("  -- {}级 {}".format(duty["min_lvl"], duty["n"]))
            i += 1
        result.append("")

    if "quests" in item.keys():
        hasSource = True
        result.append("·任务奖励")
        i = 0
        for questIndex in item["quests"]:
            if i > 4:
                result.append(f"等共计{len(item['instance'])}个任务奖励")
                break
            quest = partials[("quest", str(questIndex))]
            result.append(
                "  -- {}\n{}".format(
                    quest["n"], f"https://garlandtools.cn/db/#quest/{quest['i']}"
                )
            )
            i += 1
        result.append("")

    if not hasSource:
        result.append("获取方式较麻烦/没查到，烦请打开网页查看！")

    status = ""

    if "unique" in item.keys():
        status += "独占 "

    if "tradeable" in item.keys():
        status += f"{'' if bool(item['tradeable']) else '不'}可交易 "

    if "unlistable" in item.keys():
        status += f"{'不' if bool(item['unlistable']) else ''}可在市场上交易 "

    if "reducible" in item.keys():
        status += f"{'' if bool(item['reducible']) else '不'}可精选 "

    if "storable" in item.keys():
        status += f"{'' if bool(item['storable']) else '不'}可放入收藏柜 "

    if not status.isspace():
        result.append(status)

    url = f"https://garlandtools.{'cn' if name_lang == 'chs' else 'org'}/db/#item/{item_id}"

    return result[0], "\n".join(result), img_urls, url


async def get_xivapi_item(item_name, name_lang=""):
    api_base = CAFEMAKER if name_lang == "cn" else XIVAPI
    url = api_base + "/search?indexes=Item&string=" + item_name
    if name_lang:
        url = url + "&language=" + name_lang
    async with aiohttp.ClientSession() as client:
        r = await client.get(url, timeout=3)
        j = await r.json(content_type=None)
    return j, url


FF14WIKI_BASE_URL = "https://ff14.huijiwiki.com"


async def search_item(name) -> Tuple[str, str, List[str], str]:
    try:
        name_lang = None
        for lang in ["cn", "en", "ja", "fr", "de"]:
            j, _ = await get_xivapi_item(name, lang)
            if j.get("Results"):
                name_lang = lang
                break
        if name_lang is None:
            return "", "", [], None
        # api_base = CAFEMAKER if name_lang == "cn" else XIVAPI
        res_num = j["Pagination"]["ResultsTotal"]

        if res_num >= 1:
            try:
                return await parse_item_garland(j["Results"][0]["ID"], name_lang)
            except Exception as e:
                logger.warning(f"FFXIVWIKI: 搜索失败 {e}")
                return "", "", [], None
        return "", "", [], None

        # if res_num == 1 or j["Results"][0]["Name"] == name:
        #     try:
        #         return await parse_item_garland(j["Results"][0]["ID"], name_lang)
        #     except Exception as e:
        #         logger.warning(f"FFXIVWIKI: 搜索失败 {e}")
        #         return "", "", [], None
        # else:
        #     search_url = (
        #         FF14WIKI_BASE_URL + "/wiki/ItemSearch?name=" + urllib.parse.quote(name)
        #     )
        #     return (
        #         name,
        #         f"在灰机WIKI中找到了{res_num}个物品\n请打开链接查看",
        #         [api_base + j["Results"][0]["Icon"]],
        #         search_url,
        #     )
    except Exception as e:
        logger.warning(f"搜索最终幻想WIKI异常: {e}")
        return "", "", [], None


async def get_ffxivwiki(keyword: str) -> Tuple[str, str, str]:
    title, content, img_urls, url = await search_item(keyword)
    if not content:
        return "", "", ""
    msg = content
    if img_urls:
        msg += "<div>"
        for img in img_urls:
            msg += f'<img width="50%" src="{img}"/>'
        msg += "</div>"
    return title, msg, url
