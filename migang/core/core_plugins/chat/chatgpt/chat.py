import re
import asyncio
import traceback
from typing import Tuple
from datetime import datetime

from nonebot.log import logger
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment, GroupMessageEvent

from migang.core import sync_get_config
from migang.core.models import ChatGPTChatHistory

from .extension import extension_manager
from .openai_func import set_memory, text_generator
from .prompt import update_impression, get_chat_prompt_template
from .utils import get_bot_name, gen_chat_text, get_user_name, serialize_message

ignore_prefix: Tuple[str] = tuple(
    sync_get_config("ignore_prefix", plugin_name="chat_chatgpt", default_value=[]) or []
)
openai_timeout: int = sync_get_config(
    "timeout", plugin_name="chat_chatgpt", default_value=60
)
max_response_per_msg: int = sync_get_config(
    "max_response_per_msg", plugin_name="chat_chatgpt", default_value=5
)


async def pre_check(event: GroupMessageEvent, bot: Bot, state: T_State) -> bool:
    sender_name = await get_user_name(
        bot=bot, group_id=event.group_id, user_id=event.user_id
    )
    plain_text = event.get_plaintext()
    if not plain_text:
        logger.debug("空消息，不处理")
        return False
    if plain_text.startswith(ignore_prefix):
        logger.debug("忽略消息前缀")
        return False
    chat_text, is_tome = await gen_chat_text(event=event, bot=bot)
    is_tome = is_tome or event.is_tome()
    bot_name = get_bot_name(bot=bot)

    # 是否需要响应
    triggered = is_tome or (bot_name.lower() in chat_text.lower())

    # 记录消息，虽然可能与我无关，但是记录保证对上下文的理解
    record_msg = serialize_message(event.message)
    if is_tome:
        record_msg = [
            {"type": "at", "data": {"qq": bot.self_id}},
            {"type": "text", "data": {"text": " "}},
        ] + record_msg
    await ChatGPTChatHistory(
        user_id=event.user_id,
        group_id=event.group_id,
        message=record_msg,
        triggered=triggered,
    ).save()

    if triggered:
        logger.debug("符合发言条件，开始回复")
        # 保存信息，用于回复
        state["gpt_sender_name"] = sender_name
        state["gpt_trigger_text"] = chat_text
        state["gpt_loop_data"] = {}
        state["gpt_loop_times"] = 0
    return triggered


async def do_chat(
    matcher: Matcher, event: GroupMessageEvent, bot: Bot, state: T_State
) -> None:
    trigger_text = state["gpt_trigger_text"]
    sender_name = state["gpt_sender_name"]
    loop_data = state["gpt_loop_data"]
    loop_times = state["gpt_loop_times"]
    bot_name = get_bot_name(bot)

    # 重置唤醒
    wake_up = False

    start_time = datetime.now()

    # 生成会话模板
    prompt_template = await get_chat_prompt_template(
        bot=bot, group_id=event.group_id, user_id=event.user_id
    )

    time_before_request = datetime.now()
    raw_res, success = await text_generator.get_response(
        prompt=prompt_template,
        type="chat",
        custom={"bot_name": bot_name, "sender_name": sender_name},
    )
    if not success:  # 如果生成对话结果失败，则直接返回
        logger.warning("生成对话结果失败，跳过处理...")
        await matcher.finish(raw_res)
    if (datetime.now() - time_before_request).seconds > openai_timeout:
        logger.warning(f"OpenAI响应超过timeout值[{openai_timeout}]，停止处理")
        return

    # 提取后去除所有markdown格式的代码块，剩余部分为对话结果
    talk_res = re.sub(r"```(.+?)```", "", raw_res)

    # 分割对话结果提取出所有 "/#扩展名&参数1&参数2#/" 格式的扩展调用指令 参数之间用&分隔 多行匹配
    ext_calls = re.findall(r"/.?#(.+?)#.?/", talk_res, re.S)

    # 对分割后的对话根据 '*;' 进行分割，表示对话结果中的分句，处理结果为列表，其中每个元素为一句话
    # 提取后去除所有扩展调用指令并切分信息，剩余部分为对话结果 多行匹配
    talk_res = re.sub(r"/.?#(.+?)#.?/", "*;", talk_res)
    reply_list = talk_res.split("*;")  # 用于存储最终回复顺序内容的列表

    # 遍历所有扩展调用指令
    for ext_call_str in ext_calls:
        ext_name, *ext_args = ext_call_str.split("&")
        ext_name = ext_name.strip().lower()
        if extension := extension_manager.get_extension(name=ext_name):
            # 提取出扩展调用指令中的参数为字典
            ext_args_dict: dict = {}
            # 按照参数顺序依次提取参数值
            for arg_name in extension.parameter:
                if len(ext_args) > 0:
                    ext_args_dict[arg_name] = ext_args.pop(0)
                else:
                    ext_args_dict[arg_name] = None

            logger.info(f"检测到扩展调用指令: {ext_name} {ext_args_dict} | 正在调用扩展模块...")
            ext_args_dict.update(
                {
                    "bot_name": bot_name,
                    "user_send_raw_text": trigger_text,
                    "bot_send_raw_text": raw_res,
                }
            )
            try:  # 调用扩展的call方法
                ext_res: dict = await extension.run(ext_args_dict)
                logger.debug(f"扩展 {ext_name} 返回结果: {ext_res}")
                if ext_res is not None:
                    # 将扩展返回的结果插入到回复列表的最后
                    reply_list.append(ext_res)
            except Exception as e:
                logger.error(f"调用扩展 {ext_name} 时发生错误: {e}")
                logger.debug(f"[扩展 {ext_name}] 错误详情: {traceback.format_exc()}")
                ext_res = None
                # 将错误的调用指令从原始回复中去除，避免bot从上下文中学习到错误的指令用法
                raw_res = re.sub(r"/.?#(.+?)#.?/", "", raw_res)
        else:
            logger.warning(f"未找到扩展 {ext_name}，跳过调用...")
            # 将错误的调用指令从原始回复中去除，避免bot从上下文中学习到错误的指令用法
            raw_res = re.sub(r"/.?#(.+?)#.?/", "", raw_res)

    # 根据回复内容列表逐条发送回复
    res_times = max_response_per_msg
    for reply in reply_list[:max_response_per_msg]:
        # 判断回复内容是否为str
        if isinstance(reply, str) and reply.strip():
            reply = reply.strip()
            # 判断文本内容是否为纯符号(包括空格，换行、英文标点、中文标点)并且长度小于3
            if re.match(r"^[^\u4e00-\u9fa5\w]{1}$", reply):
                logger.debug(f"检测到纯符号文本: {reply}，跳过发送...")
                continue
            logger.info(f"回复文本消息: {reply}")
            await matcher.send(reply)
        else:
            for key in reply:  # 遍历回复内容类型字典
                if key == "text" and reply.get(key) and reply.get(key).strip():  # 发送文本
                    # 判断文本内容是否为纯符号(包括空格，换行、英文标点、中文标点)并且长度为1
                    if re.match(r"^[^\u4e00-\u9fa5\w]{1}$", reply.get(key).strip()):
                        logger.debug(f"检测到纯符号文本: {reply.get(key).strip()}，跳过发送...")
                        continue
                    await matcher.send(reply.get(key).strip())
                    logger.info(f"回复文本消息: {reply.get(key).strip()}")
                elif key == "image" and reply.get(key):  # 发送图片
                    await matcher.send(MessageSegment.image(reply.get(key)))
                    logger.info(f"回复图片消息: {reply.get(key)}")
                elif key == "voice" and reply.get(key):  # 发送语音
                    logger.info(f"回复语音消息: {reply.get(key)}")
                    await matcher.send(
                        Message(MessageSegment.record(file=reply.get(key), cache=0))
                    )
                elif key == "code_block" and reply.get(key):  # 发送代码块
                    await matcher.send(Message(reply.get(key).strip()))
                elif key == "memory" and reply.get(key):  # 记忆存储
                    logger.info(f"存储记忆: {reply.get(key)}")
                    await set_memory(
                        group_id=event.group_id,
                        user_id=event.user_id,
                        mem_key=reply.get(key).get("key"),
                        mem_value=reply.get(key).get("value"),
                    )
                elif key == "notify" and reply.get(key):  # 通知消息
                    if "sender" in reply.get(key) and "msg" in reply.get(key):
                        loop_data["notify"] = reply.get(key)
                    else:
                        logger.warning(f"通知消息格式错误: {reply.get(key)}")
                elif key == "wake_up" and reply.get(key):  # 重新调用对话
                    logger.info(f"重新调用对话: {reply.get(key)}")
                    wake_up = reply.get(key)
                elif key == "timer" and reply.get(key):  # 定时器
                    logger.info(f"设置定时器: {reply.get(key)}")
                    loop_data["timer"] = reply.get(key)

                res_times -= 1
                if res_times < 1:  # 如果回复次数超过限制，则跳出循环
                    break
        await asyncio.sleep(1.5)  # 每条回复之间间隔1.5秒

    cost_token = text_generator.cal_token_count(
        str(prompt_template) + raw_res
    )  # 计算对话结果的 token 数量

    logger.debug(f'token消耗: {cost_token} | 对话响应: "{raw_res}"')

    # 记录回复
    await ChatGPTChatHistory(
        user_id=event.self_id,
        group_id=event.group_id,
        message=serialize_message(raw_res),
        target_id=event.user_id,
    ).save()

    # 更新印象
    await update_impression(bot=bot, group_id=event.group_id, user_id=event.user_id)

    logger.debug(f"对话响应完成 | 耗时: {(datetime.now() - start_time).seconds}s")

    # 检查是否再次触发对话
    if wake_up and loop_times < 3:
        if "notify" in loop_data:  # 如果存在定时器或通知消息，将其作为触发消息再次调用对话
            if time_diff := loop_data.get("timer"):
                if time_diff > 0:
                    logger.debug(f"等待 {time_diff}s 后再次调用对话...")
                    await asyncio.sleep(time_diff)
                    logger.debug(f"再次调用对话...")
            state["gpt_trigger_text"] = loop_data.get("notify", {}).get("msg", "")
            state["gpt_sender_name"] = loop_data.get("notify", {}).get(
                "sender", "[system]"
            )
            state["gpt_loop_times"] += 1
            await ChatGPTChatHistory(
                user_id=event.user_id,
                group_id=event.group_id,
                message=serialize_message(state["gpt_trigger_text"]),
            ).save()
            await do_chat(
                matcher=matcher,
                event=event,
                bot=bot,
            )
