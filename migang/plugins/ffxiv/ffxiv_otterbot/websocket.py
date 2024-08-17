import re
import time
import asyncio
from typing import Any
from asyncio import Queue

import ujson
import websockets
from nonebot import get_bot
from nonebot.log import logger
from pydantic import BaseModel
from nonebot.adapters import Event
from websockets import WebSocketClientProtocol
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

_HEARTBEAT_INTERVAL = 30


def _get_heartbeat_event(bot_id: str) -> str:
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
    if message:
        if isinstance(message, str) and (
            match := re.search(_reply_id_pattern, message)
        ):
            data["params"]["message"] = MessageSegment.reply(match.group(1)) + Message(
                message.replace(match.group(0), "").strip()
            )
        if isinstance(message, list):
            new_message = Message()
            if message[-1]["type"] == "reply":
                new_message.append(MessageSegment.reply(message[-1]["data"]["id"]))
                message = message[:-1]
            for m in message:
                new_message.append(MessageSegment(type=m["type"], data=m["data"]))
            data["params"]["message"] = new_message


class WebSocketConn:
    def __init__(self, url: str, bot_id: int, access_token: str) -> None:
        self.__queue = Queue()
        self.__url = url
        self.__bot_id = bot_id
        self.__bot_id_str = str(bot_id)
        self.__access_token = access_token
        self.__send_task = None
        self.__recv_task = None
        self.__heartbeat = None
        self.__stop_flag = False
        self.__connect = False
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
                    max_size=50 * 1024 * 1024,
                ) as websocket:
                    logger.info("与獭窝已成功建立连接")
                    self.__websocket = websocket
                    self.__connect = True
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
                    "<y><bg #f8bbd0>与獭窝连接关闭</bg #f8bbd0></y>"
                )
            except Exception as e:
                logger.opt(colors=True).error(
                    f"<y><bg #f8bbd0>连接獭窝发生意料之外的错误：{e}</bg #f8bbd0></y>"
                )
                import traceback

                traceback.print_exc()
            finally:
                # 无论哪种异常，都处理断开连接的逻辑
                await self.__handle_disconnect()
                # 等待5s重连
                await asyncio.sleep(5)

    async def __send_heartbeat(self, ws: WebSocketClientProtocol):
        while self.__connect:
            try:
                await asyncio.sleep(_HEARTBEAT_INTERVAL)
                await ws.send(_get_heartbeat_event(self.__bot_id))
            except (ConnectionClosedError, ConnectionClosedOK) as e:
                raise e
            except Exception as e:
                logger.warning(f"发送心跳事件失败：{e}")

    async def __handle_disconnect(self):
        self.__connect = False
        if self.__send_task:
            self.__send_task.cancel()
            try:
                await self.__send_task
            except asyncio.CancelledError:
                logger.info("send_task已取消")
            except Exception as e:
                logger.warning(f"send_task 错误: {e}")

        if self.__recv_task:
            self.__recv_task.cancel()
            try:
                await self.__recv_task
            except asyncio.CancelledError:
                logger.info("recv_task已取消")
            except Exception as e:
                logger.warning(f"recv_task 错误: {e}")

        if self.__heartbeat:
            self.__heartbeat.cancel()
            try:
                await self.__heartbeat
            except asyncio.CancelledError:
                logger.info("heartbeat已取消")
            except Exception as e:
                logger.warning(f"heartbeat 错误: {e}")

        try:
            await self.__websocket.close()
        except Exception as e:
            logger.info(f"ws连接关闭：{e}")

    async def stop(self):
        self.__stop_flag = False
        await self.__handle_disconnect()

    async def forwardEvent(self, event: Event):
        await self.__queue.put(event)

    async def _call_api(self, raw_data: str) -> Any:
        try:
            data = ujson.loads(raw_data)
            echo = data.get("echo", "")
            action = data["action"]
            _proccess_api(action=action, data=data)
            params = data["params"]
            bot = get_bot(self.__bot_id_str)
            resp = await bot.call_api(action, **params)
            resp_data = _build_ret_msg(resp)
            if echo:
                resp_data["echo"] = echo
            logger.info(f"发送獭窝API调用结果：{resp_data}")
            await self.__queue.put(resp_data)
        except Exception as e:
            logger.error(f"调用api失败：{raw_data}：{e}")
            import traceback

            traceback.print_exc()
            # await self.__queue.put({"status": "failed", "echo": echo})

    async def __do_send(self, data, ws: WebSocketClientProtocol):
        try:
            await ws.send(data)
        except (ConnectionClosedError, ConnectionClosedOK) as e:
            logger.warning(f"ws已断开连接，无法继续发送消息：{e}")
        except Exception as e:
            logger.warning(f"ws发送消息失败：{e}")

    async def __ws_send(self, ws: WebSocketClientProtocol):
        while self.__connect:
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
                asyncio.create_task(self.__do_send(send_data, ws))
            except (ConnectionClosedError, ConnectionClosedOK) as e:
                raise e
            except Exception as e:
                logger.error(f"发送獭窝信息异常：{e}")

    async def __ws_recv(self, ws: WebSocketClientProtocol):
        while self.__connect:
            try:
                raw_data = await ws.recv()
                logger.info(f"收到獭窝信息：{raw_data[:200]}")
                asyncio.create_task(self._call_api(raw_data))
            except (ConnectionClosedError, ConnectionClosedOK) as e:
                raise e
            except Exception as e:
                logger.error(f"接受獭窝信息异常：{e}")
