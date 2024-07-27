import re
import time
import asyncio
from typing import Any
from asyncio import Queue

import ujson
import websockets
from nonebot.log import logger
from pydantic import BaseModel
from nonebot.adapters import Bot, Event
from websockets import WebSocketClientProtocol
from nonebot.adapters.onebot.v11 import MessageSegment
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

_HEARTBEAT_INTERVAL = 3


def _get_heartbeat_event(bot_id: int) -> str:
    data = {
        "post_type": "meta_event",
        "meta_event_type": "heartbeat",
        "interval": _HEARTBEAT_INTERVAL,
        "status": {"online": True, "good": True},
        "self_id": bot_id,
        "time": int(time.time()),
    }
    return ujson.dumps(data)


def _build_ret_msg(data) -> dict[str, Any]:
    return {"status": "ok", "retcode": 0, "data": data}


_reply_id_pattern = r"\[CQ:reply,id=([^\]]+)\]"


def _proccess_api(action: str, data: dict[str, Any]):
    if action == "get_group_member_list":
        data["params"]["group_id"] = str(data["params"]["group_id"])
    message: str = data["params"].get("message")
    if message and (match := re.search(_reply_id_pattern, message)):
        data["params"]["message"] = MessageSegment.reply(
            match.group(1)
        ) + message.replace(match.group(0), "")


class WebSocketConn:
    def __init__(self, bot: Bot, url: str, bot_id: int, access_token: str) -> None:
        self.__queue = Queue()
        self.__url = url
        self.__bot_id = bot_id
        self.__access_token = access_token
        self.__bot = bot
        self.__send_task = None
        self.__recv_task = None
        self.__heartbeat = None
        self.__stop_flag = False
        self.__websocket: WebSocketClientProtocol = None

    async def connect(self):
        self.__stop_flag = True
        while self.__stop_flag:
            try:
                async with websockets.connect(
                    self.__url,
                    extra_headers={
                        "Authorization": f"Bearer {self.__access_token}",
                        "X-Self-ID": self.__bot_id,
                        "X-Client-Role": "Universal",
                        "User-Agent": "OneBot",
                    },
                ) as websocket:
                    logger.info("与獭窝已成功建立连接")
                    self.__websocket = websocket
                    self.__send_task = asyncio.create_task(self.__ws_send(websocket))
                    self.__recv_task = asyncio.create_task(self.__ws_recv(websocket))
                    self.__heartbeat = asyncio.create_task(
                        self.__send_heartbeat(websocket)
                    )
                    await asyncio.gather(
                        self.__send_task, self.__recv_task, self.__heartbeat
                    )
            except (ConnectionClosedError, ConnectionClosedOK):
                logger.opt(colors=True).warning(
                    "<y><bg #f8bbd0>WebSocket Closed</bg #f8bbd0></y>"
                )
                self.__send_task.cancel()
                self.__recv_task.cancel()
                self.__heartbeat.cancel()
                await asyncio.sleep(1)  # 等待重连

    async def __send_heartbeat(self, ws: WebSocketClientProtocol):
        while self.__stop_flag:
            try:
                await asyncio.sleep(_HEARTBEAT_INTERVAL)
                await ws.send(_get_heartbeat_event(self.__bot_id))
            except Exception as e:
                logger.error(f"发送心跳事件失败：{e}")

    async def stop(self):
        self.__stop_flag = False
        self.__send_task.cancel()
        self.__recv_task.cancel()
        self.__heartbeat.cancel()
        await self.__websocket.close()

    async def forwardEvent(self, event: Event):
        if hasattr(event, "self_id"):
            event.self_id = self.__bot_id
        await self.__queue.put(event)

    async def _call_api(self, raw_data: str) -> Any:
        echo: str = ""
        try:
            data = ujson.loads(raw_data)
            echo = data.get("echo", "")
            action = data["action"]
            _proccess_api(action=action, data=data)
            resp = await self.__bot.call_api(data["action"], **data["params"])
            resp_data = _build_ret_msg(resp)
            if echo:
                resp_data["echo"] = echo
            logger.info(f"发送獭窝API调用结果：{resp_data}")
            await self.__queue.put(resp_data)
        except Exception as e:
            logger.warning(f"调用api失败：{data}：{e}")
            import traceback

            traceback.print_exc()
            return {"status": "failed", "echo": echo}

    async def __ws_send(self, ws: WebSocketClientProtocol):
        while self.__stop_flag:
            try:
                event = await self.__queue.get()
                send_data: str
                if isinstance(event, BaseModel):
                    send_data = event.model_dump()
                    send_data["message"] = send_data["raw_message"]
                    send_data = ujson.dumps(send_data)
                elif isinstance(event, dict):
                    send_data = ujson.dumps(event)
                elif isinstance(event, str):
                    send_data = event
                asyncio.create_task(ws.send(send_data))
            except (ConnectionClosedError, ConnectionClosedOK) as e:
                raise e
            except Exception as e:
                logger.error(f"发送獭窝信息异常：{e}")

    async def __ws_recv(self, ws: WebSocketClientProtocol):
        while self.__stop_flag:
            try:
                raw_data = await ws.recv()
                logger.info(f"收到獭窝信息：{raw_data}")
                asyncio.create_task(self._call_api(raw_data))
            except (ConnectionClosedError, ConnectionClosedOK) as e:
                raise e
            except Exception as e:
                logger.error(f"接受獭窝信息异常：{e}")
