import time
import random
import asyncio
from typing import Any
from asyncio import Queue

import ujson
import websockets
from nonebot import get_bot
from nonebot.log import logger
from pydantic import BaseModel
from websockets import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment

_HEARTBEAT_INTERVAL = 30


def _proccess_api(data: dict[str, Any]):
    message: str = data["params"].get("message")
    if message:
        if isinstance(message, list):
            new_message = Message()
            for m in message:
                new_message.append(MessageSegment(type=m["type"], data=m["data"]))
            data["params"]["message"] = new_message


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


class WebSocketConn:
    def __init__(self, url: str, access_token: str) -> None:
        self.__queue = Queue()
        self.__url = url
        self.__bot_id = int("".join([str(random.randint(0, 9)) for _ in range(10)]))
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
                    logger.info("与memes已成功建立连接")
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
                    "<y><bg #f8bbd0>与memes连接关闭</bg #f8bbd0></y>"
                )
                await self.__handle_disconnect()
                await asyncio.sleep(1)  # 等待重连
            except Exception as e:
                logger.opt(colors=True).error(
                    f"<y><bg #f8bbd0>连接memes发生意料之外的错误：{e}</bg #f8bbd0></y>"
                )
                import traceback

                traceback.print_exc()
                await asyncio.sleep(15)

    async def __send_heartbeat(self, ws: WebSocketClientProtocol):
        while self.__connect:
            try:
                await asyncio.sleep(_HEARTBEAT_INTERVAL)
                await ws.send(_get_heartbeat_event(self.__bot_id))
            except Exception as e:
                logger.warning(f"memes：发送心跳事件失败：{e}")

    async def __handle_disconnect(self):
        self.__connect = False
        if self.__send_task:
            self.__send_task.cancel()
            try:
                await self.__send_task
            except asyncio.CancelledError:
                logger.info("memes：send_task已取消")
            except Exception as e:
                logger.warning(f"memes：send_task 错误: {e}")

        if self.__recv_task:
            self.__recv_task.cancel()
            try:
                await self.__recv_task
            except asyncio.CancelledError:
                logger.info("memes：recv_task已取消")
            except Exception as e:
                logger.warning(f"memes：recv_task 错误: {e}")

        if self.__heartbeat:
            self.__heartbeat.cancel()
            try:
                await self.__heartbeat
            except asyncio.CancelledError:
                logger.info("memes：heartbeat已取消")
            except Exception as e:
                logger.warning(f"memes：heartbeat 错误: {e}")

        try:
            await self.__websocket.close()
        except Exception as e:
            logger.info(f"memes：ws连接关闭：{e}")

    async def stop(self):
        self.__stop_flag = False
        await self.__handle_disconnect()

    async def forwardEvent(self, event: MessageEvent):
        await self.__queue.put(event)

    async def _call_api(self, raw_data: str) -> Any:
        echo: str = ""
        try:
            data = ujson.loads(raw_data)
            echo = data.get("echo", "")
            action = data["action"]
            params = data["params"]
            _proccess_api(data)
            bot = get_bot(str(params.get("__self_id__")))
            resp = await bot.call_api(action, **params)
            resp_data = _build_ret_msg(resp)
            if echo:
                resp_data["echo"] = echo
            logger.info(f"发送memesAPI调用结果：{resp_data}")
            await self.__queue.put(resp_data)
        except Exception as e:
            logger.error(f"memes：调用api失败：{data}：{e}")
            import traceback

            traceback.print_exc()
            # await self.__queue.put({"status": "failed", "echo": echo})

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
                asyncio.create_task(ws.send(send_data))
            except (ConnectionClosedError, ConnectionClosedOK) as e:
                raise e
            except Exception as e:
                logger.error(f"发送memes信息异常：{e}")
            finally:
                self.__queue.task_done()

    async def __ws_recv(self, ws: WebSocketClientProtocol):
        while self.__connect:
            try:
                raw_data = await ws.recv()
                logger.info(f"收到memes信息：{raw_data[:200]}")
                asyncio.create_task(self._call_api(raw_data))
            except (ConnectionClosedError, ConnectionClosedOK) as e:
                raise e
            except Exception as e:
                logger.error(f"接受memes信息异常：{e}")
