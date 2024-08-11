from asyncio import gather
from time import strftime, localtime
from typing import Dict, List, Union

from nonebot.log import logger
from nonebot.rule import to_me
from pil_utils import text2image
from nonebot.permission import SUPERUSER
from nonebot import get_bot, on_fullmatch
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_htmlrender import get_new_page
from tenacity import RetryError, retry, wait_random, stop_after_attempt
from nonebot.adapters.onebot.v11 import GROUP, MessageSegment, GroupMessageEvent

from migang.utils.image import pic_to_bytes
from migang.utils.file import async_load_data, async_save_data
from migang.core import (
    TaskItem,
    ConfigItem,
    broadcast,
    check_task,
    get_config,
    sync_get_config,
    post_init_manager,
)

from ._utils import get_image_cqcode
from .weibo_spider import (
    UserWeiboSpider,
    KeywordWeiboSpider,
    weibo_record_path,
    weibo_id_name_file,
)

tasks_dict: Dict[str, List[Union[UserWeiboSpider, KeywordWeiboSpider]]] = {}


def _load_config():
    try:
        weibo_record_path.mkdir(parents=True, exist_ok=True)
        default_format = sync_get_config("default_format")
        configs = sync_get_config("WeiboSubs")
        for task_name, v in configs.items():
            users = v["users"]
            if "format" in v:
                cur_format = v["format"]
            else:
                cur_format = default_format
            task_spider_list = []
            for user in users:
                if "format" not in user:
                    user["format"] = cur_format
                if "keyword" in user:
                    wb_spider = KeywordWeiboSpider(user)
                elif "user_id" in user:
                    wb_spider = UserWeiboSpider(user)
                task_spider_list.append(wb_spider)
            __plugin_task__.append(
                TaskItem(
                    task_name=task_name,
                    name=v["description"],
                    default_status=v["enable_on_default"],
                    usage=f"微博推送组 {v['description']} 的启闭状态",
                    description=f"微博推送组 {v['description']}",
                )
            )
            tasks_dict[task_name] = task_spider_list
    except Exception as e:
        logger.error(f"微博推送配置文件解析失败：{e}")


__plugin_meta__ = PluginMetadata(
    name="微博推送",
    description="自动推送微博（可推送范围由维护者设定）",
    usage="""
usage：
    自动推送微博（可推送范围由维护者设定）
    发送[可订阅微博列表]（需要at）可查看订阅列表
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_category__ = "订阅"
__plugin_config__ = [
    ConfigItem(
        key="forward_mode",
        initial_value=False,
        default_value=False,
        description="是否以转发模式推送微博，当配置项为true时将以转发模式推送",
    ),
    ConfigItem(
        key="default_format",
        initial_value=1,
        default_value=1,
        description="默认推送格式：0 文本，1 图片",
    ),
    ConfigItem(
        key="cookie",
        initial_value=None,
        default_value=None,
        description="添加 m.weibo.cn 的cookie后可以获取到更多的微博",
    ),
    ConfigItem(
        key="WeiboSubs",
        initial_value={
            "weibo-ff14": {
                "description": "最终幻想14微博推送",
                "enable_on_default": False,
                "format": 1,
                "users": [
                    {
                        "user_id": "1797798792",
                        "filter_retweet": False,
                        "filter_words": ["微博抽奖平台"],
                    },
                    {
                        "user_id": "1794603954",
                        "filter_retweet": False,
                        "filter_words": [],
                    },
                    {
                        "user_id": "7316752765",
                        "filter_retweet": False,
                        "filter_words": [],
                    },
                ],
            },
            "weibo-ShiningNikki": {
                "description": "闪耀暖暖微博推送",
                "enable_on_default": False,
                "format": 0,
                "users": [
                    {
                        "user_id": "6498105282",
                        "format": 1,
                        "filter_retweet": False,
                        "filter_words": [],
                    },
                    {
                        "user_id": "6775494073",
                        "filter_retweet": False,
                        "filter_words": [],
                    },
                    {
                        "user_id": "6476598194",
                        "filter_retweet": False,
                        "filter_words": [],
                    },
                ],
            },
            "weibo-keyword": {
                "description": "包含关键词的微博推送",
                "enable_on_default": False,
                "format": 0,
                "users": [
                    {
                        "keyword": "苏暖暖",
                        "format": 1,
                        "filter_retweet": False,
                        "filter_words": [],
                    },
                ],
            },
        },
        default_value={},
        description="""
微博推送组的配置
单个组的键值对应task名
description对应群被动状态中任务名
format为当前组的模式，若无该项则默认为全局配置
users为当前推送组的用户，其中：

user_id为https://weibo.com/u/xxxxx的xxxx
keyword为需要检测的关键词，当存在keyword时，user_id将被忽略

format为当前用户的模式，若无该项则默认为外层配置
filter_retweet为是否过滤转发的微博
filter_words为过滤词，包含过滤词的微博不推送
""".strip(),
    ),
]

__plugin_task__ = []
try:
    _load_config()
except Exception as e:
    logger.warning(f"微博推送加载异常，若初次加载微博推送，请等待配置文件生成完成并按需修改后重新启动：{e}")

weibo_list = on_fullmatch(
    ("可订阅微博列表", "weibo-list"),
    rule=to_me(),
    permission=GROUP,
    priority=5,
    block=True,
)

weibo_update_username = on_fullmatch(
    "更新微博用户名",
    rule=to_me(),
    permission=SUPERUSER,
    priority=5,
    block=True,
)

forward_mode = False


@post_init_manager
async def _():
    global forward_mode
    forward_mode = await get_config("forward_mode")
    tasks = []
    for spiders in tasks_dict.values():
        for spider in spiders:
            tasks.append(spider.init())
    try:
        await gather(*tasks)
        logger.info("微博推送初始化完成")
    except Exception as e:
        logger.error(f"微博推送初始化异常: {e}")


@weibo_list.handle()
async def _(event: GroupMessageEvent):
    group_id = event.group_id
    msg = "以下为可订阅微博列表，请发送[开启 xxx]来订阅\n=====================\n"
    ret = []
    for task in __plugin_task__:
        tmp = f'{task.name}[{"✔" if check_task(group_id, task.task_name) else "❌"}]:'
        users = []
        for spider in tasks_dict[task.task_name]:
            users.append(
                f"{spider.get_notice_name()}[{'图片' if spider.get_format() == 1 else '文本'}]"
            )
        ret.append(tmp + " ".join(users))
    await weibo_list.finish(
        MessageSegment.image(
            pic_to_bytes(text2image(text=msg + "\n\n".join(ret) + "\n"))
        )
    )


@weibo_update_username.handle()
async def _():
    await weibo_update_username.send("开始更新微博用户名")
    await update_user_name()
    await weibo_update_username.send("微博用户名更新结束")


async def wb_to_text(wb: Dict):
    msg = f"{wb['screen_name']}'s Weibo:\n====================="
    # id = wb["id"]
    bid = wb["bid"]
    time = wb["created_at"]
    if "retweet" in wb:
        msg = f"{msg}\n{wb['text']}\n=========转发=========\n>>转发@{wb['retweet']['screen_name']}"
        wb = wb["retweet"]
    msg += f"\n{wb['text']}"
    if len(wb["pics"]) > 0:
        image_urls = wb["pics"]
        msg += "\n"
        res_imgs = await gather(*[get_image_cqcode(url) for url in image_urls])
        for img in res_imgs:
            msg += img

    if len(wb["video_poster_url"]) > 0:
        video_posters = wb["video_poster_url"]
        msg += "\n[视频封面]\n"
        video_imgs = await gather(*[get_image_cqcode(url) for url in video_posters])
        for img in video_imgs:
            msg += img

    msg += f"\nURL:https://m.weibo.cn/detail/{bid}\n时间: {strftime('%Y-%m-%d %H:%M', localtime(time))}"

    return msg


async def wb_to_image(wb: Dict) -> bytes:
    msg = f"{wb['screen_name']}'s Weibo:\n"
    url = f"https://m.weibo.cn/detail/{wb['bid']}"
    time = wb["created_at"]

    @retry(wait=wait_random(min=1, max=2), stop=stop_after_attempt(3))
    async def get_screenshot():
        async with get_new_page(
            is_mobile=True, viewport={"width": 2048, "height": 2732}
        ) as page:
            await page.goto(
                url,
                wait_until="networkidle",
            )
            # await page.wait_for_selector(".ad-wrap", state="attached", timeout=8 * 1000)
            # await page.eval_on_selector(
            #     selector=".ad-wrap",
            #     expression="(el) => el.style.display = 'none'",
            # )
            # 去除“小程序看微博热搜”横幅
            card = await page.wait_for_selector(
                "xpath=//div[@class='card m-panel card9 f-weibo']",
                timeout=6 * 1000,
            )
            try:
                await card.wait_for_selector(".wrap", state="attached", timeout=30)
                await card.eval_on_selector(
                    selector=".wrap",
                    expression="(el) => el.style.display = 'none'",
                )
            except Exception:
                logger.info("似乎没有“小程序看微博热搜”横幅？")
            img = await card.screenshot()
            return (
                msg
                + MessageSegment.image(img)
                + f"\n{url}\n时间: {strftime('%Y-%m-%d %H:%M', localtime(time))}"
            )

    try:
        return await get_screenshot()
    except RetryError:
        logger.warning(f"截取微博 {url} 图片失败，将尝试以文字形式发送")
    return None


async def process_wb(format_: int, wb: Dict):
    if (
        not wb["only_visible_to_fans"]
        and format_ == 1
        and (msg := await wb_to_image(wb))
    ):
        return msg
    return await wb_to_text(wb)


interval = 0
for spiders in tasks_dict.values():
    interval += 26 * len(spiders)


@scheduler.scheduled_job("interval", seconds=interval, jitter=10)
async def _():
    for task, spiders in tasks_dict.items():
        weibos = []
        for spider in spiders:
            latest_weibos = await spider.get_latest_weibos()
            format_ = spider.get_format()
            formatted_weibos = [(await process_wb(format_, wb)) for wb in latest_weibos]
            if weibo_num := len(formatted_weibos):
                logger.info(f"成功获取{spider.get_notice_name()}的新微博{weibo_num}条")
            else:
                logger.info(f"未检测到{spider.get_notice_name()}的新微博")
            weibos += formatted_weibos
        if weibos:
            bot = get_bot()
            if forward_mode:
                weibos = [
                    MessageSegment.node_custom(bot.self_id, "微博威", weibo)
                    for weibo in weibos
                ]
            await broadcast(task_name=task, msg=weibos, forward=forward_mode)


@scheduler.scheduled_job("cron", second="0", minute="0", hour="5")
async def clear_spider_buffer():
    logger.info("Cleaning weibo spider buffer...")
    tasks = []
    for spiders in tasks_dict.values():
        tasks += [spider.clear_buffer() for spider in spiders]
    await gather(*tasks)


@scheduler.scheduled_job("cron", second="0", minute="0", hour="4")
async def update_user_name():
    logger.info("Updating weibo user_name...")
    id_name_map = await async_load_data(weibo_id_name_file)
    modified = False
    for _, spiders in tasks_dict.items():
        for spider in spiders:
            if isinstance(spider, UserWeiboSpider):
                if uname := await spider.update_username():
                    id_name_map[spider.get_userid()] = uname
                    modified = True
    if modified:
        await async_save_data(id_name_map, weibo_id_name_file)
