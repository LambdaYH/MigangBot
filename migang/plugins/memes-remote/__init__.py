import asyncio

from nonebot.drivers import Driver
from nonebot.plugin import PluginMetadata
from nonebot import get_driver, on_message
from nonebot.adapters.onebot.v11 import MessageEvent

from migang.core import ConfigItem, get_config, post_init_manager

from .websocket import WebSocketConn

__plugin_meta__ = PluginMetadata(
    name="memes-remote",
    description="表情包制作",
    usage="""
[md][width=1000]
  #### 表情列表

  发送 “表情包制作” 显示表情列表：

  #### 表情帮助

  - 发送 “表情详情 + 表情名/关键词” 查看 表情详细信息 和 表情预览

  #### 表情包开关

  群主 / 管理员 / 超级用户 可以启用或禁用某些表情包

  发送 `启用表情/禁用表情 [表情名/表情关键词]`，如：`禁用表情 摸`

  超级用户 可以设置某个表情包的管控模式（黑名单/白名单）

  发送 `全局启用表情 [表情名/表情关键词]` 可将表情设为黑名单模式；

  发送 `全局禁用表情 [表情名/表情关键词]` 可将表情设为白名单模式；

  #### 表情使用

  发送 “关键词 + 图片/文字” 制作表情

  可使用 “自己”、“@某人” 获取指定用户的头像作为图片

  可使用 “@ + 用户id” 指定任意用户获取头像，如 “摸 @114514”

  可回复包含图片的消息作为图片输入

  #### 随机表情

  发送 “随机表情 + 图片/文字” 可随机制作表情

  随机范围为 图片/文字 数量符合要求的表情
""".strip(),
    type="application",
    supported_adapters={"~onebot.v11"},
)
__plugin_category__ = "好玩的"

__plugin_config__ = [ConfigItem(
    key = "url",
    initial_value= "",
    description="连接地址"
),
ConfigItem(
    key = "access_token",
    initial_value= "",
    description="token"
)
]

driver: Driver = get_driver()

ws_conn: WebSocketConn

async def _handler(event: MessageEvent):
    await ws_conn.forwardEvent(event)


@post_init_manager
async def setup_ws():
    url = await get_config("url")
    if not url:
        return
    ascess_token = await get_config("access_token")
    global ws_conn
    ws_conn = WebSocketConn(
        url=url, access_token=ascess_token
    )
    on_message(block=False, priority=20).append_handler(_handler)
    asyncio.create_task(ws_conn.connect())
