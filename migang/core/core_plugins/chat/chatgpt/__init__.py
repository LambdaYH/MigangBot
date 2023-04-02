import re
import time
import asyncio
import traceback
from typing import Tuple

from nonebot import require
from nonebot.log import logger
from cachetools import TTLCache
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment, GroupMessageEvent

from ..exception import BreakSession
from .naturel_gpt.config import config
from .naturel_gpt.openai_func import TextGenerator
from .naturel_gpt.Extension import global_extensions
from .naturel_gpt.chat_manager import Chat, ChatManager
from .naturel_gpt.matcher import handler, do_msg_response
from .naturel_gpt.utils import gen_chat_text, get_user_name
from .naturel_gpt.persistent_data_manager import PersistentDataManager

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import text_to_pic


async def get_gpt_chat(matcher: Matcher, event: GroupMessageEvent, bot: Bot):
    await handler(matcher_=matcher, event=event, bot=bot)
    raise BreakSession("由naturel_gpt处理发送逻辑")


# 昵称缓存10分钟
# 键值为（群号，用户号）
sender_name_cache: TTLCache[Tuple[int, int]] = TTLCache(maxsize=1024, ttl=60 * 10)


async def not_at_rule(bot: Bot, event: GroupMessageEvent, state: T_State) -> bool:
    # 只响应非at事件，at事件让别的去管
    if event.is_tome():
        return False

    # 判断用户账号是否被屏蔽
    if event.get_user_id() in config.FORBIDDEN_USERS:
        return False

    # 如果是忽略前缀 或者 消息为空，则跳过处理
    if (
        event.get_plaintext().strip().startswith(config.IGNORE_PREFIX)
        or not event.get_plaintext()
    ):
        return False

    chat_key = "group_" + event.get_session_id().split("_")[1]

    sender_name = sender_name_cache.get((event.group_id, event.user_id))
    if sender_name is None:
        sender_name = (
            await get_user_name(event=event, bot=bot, user_id=event.user_id) or "未知"
        )
        sender_name_cache[(event.group_id, event.user_id)] = sender_name

    trigger_text, wake_up = await gen_chat_text(event=event, bot=bot)
    chat: Chat = ChatManager.instance.get_or_create_chat(chat_key=chat_key)

    if config.REPLY_ON_NAME_MENTION and (
        chat.get_chat_preset_key().lower() in trigger_text.lower()
    ):
        # 更新全局对话历史记录
        # chat.update_chat_history_row(sender=sender_name, msg=trigger_text, require_summary=True)
        await chat.update_chat_history_row(
            sender=sender_name,
            msg=trigger_text,
            require_summary=False,
        )
        # 保存信息，用于回复
        state["gpt_trigger_userid"] = event.get_user_id()
        state["gpt_sender_name"] = sender_name
        state["gpt_trigger_text"] = trigger_text
        state["gpt_chat"] = chat
        state["gpt_chat_key"] = chat_key
        state["gpt_is_tome"] = wake_up
        return True
    # 和Bot无关，记录但是不处理
    if config.CHAT_ENABLE_RECORD_ORTHER:
        await chat.update_chat_history_row(
            sender=sender_name, msg=trigger_text, require_summary=False
        )
    return False


async def not_at_handler(matcher: Matcher, state: T_State):
    # 进行回复，初始化所需
    chat = state["gpt_chat"]
    trigger_text = state["gpt_trigger_text"]
    sender_name = state["gpt_sender_name"]
    trigger_userid = state["gpt_trigger_userid"]
    chat_key = state["gpt_chat_key"]
    is_tome = state["gpt_is_tome"]
    loop_data = {}
    loop_times = 0

    wake_up = False  # 进入对话流程，重置唤醒状态

    # 记录对用户的对话信息
    await chat.update_chat_history_row_for_user(
        sender=sender_name,
        msg=trigger_text,
        userid=trigger_userid,
        username=sender_name,
        require_summary=False,
    )

    sta_time: float = time.time()

    # 生成对话 prompt 模板
    prompt_template = chat.get_chat_prompt_template(userid=trigger_userid)

    time_before_request = time.time()
    tg = TextGenerator.instance
    raw_res, success = await tg.get_response(
        prompt=prompt_template,
        type="chat",
        custom={"bot_name": chat.get_chat_preset_key(), "sender_name": sender_name},
    )  # 生成对话结果
    if not success:  # 如果生成对话结果失败，则直接返回
        logger.warning("生成对话结果失败，跳过处理...")
        await matcher.finish(raw_res)

    # 输出对话原始响应结果
    if config.DEBUG_LEVEL > 0:
        logger.info(f"原始回应: {raw_res}")

    if time.time() - time_before_request > config.OPENAI_TIMEOUT:
        logger.warning(f"OpenAI响应超过timeout值[{config.OPENAI_TIMEOUT}]，停止处理")
        return

    # 用于存储最终回复顺序内容的列表
    reply_list = []

    # 预检一次响应内容，如果响应内容中包含了需要打断的扩展调用指令，则直接截断原始响应中该扩展调用指令后的内容
    pre_check_calls = re.findall(r"/#(.+?)#/", raw_res, re.S)
    if pre_check_calls:
        for call_str in pre_check_calls:
            ext_name, *ext_args = call_str.split("&")
            ext_name = ext_name.strip().lower()
            if ext_name in global_extensions and global_extensions[
                ext_name
            ].get_config().get("interrupt", False):
                # 获取该扩展调用指令结束在原始响应中的位置
                call_end_pos = raw_res.find(f"/#{call_str}#/") + len(f"/#{call_str}#/")
                # 截断原始响应内容
                raw_res = raw_res[:call_end_pos]
                if config.DEBUG_LEVEL > 0:
                    logger.warning(f"检测到需要打断的扩展调用指令: {call_str}, 已截断原始响应内容")
                break

    # 提取后去除所有markdown格式的代码块，剩余部分为对话结果
    talk_res = re.sub(r"```(.+?)```", "", raw_res)

    # 分割对话结果提取出所有 "/#扩展名&参数1&参数2#/" 格式的扩展调用指令 参数之间用&分隔 多行匹配
    ext_calls = re.findall(r"/.?#(.+?)#.?/", talk_res, re.S)

    # 对分割后的对话根据 '*;' 进行分割，表示对话结果中的分句，处理结果为列表，其中每个元素为一句话
    if config.NG_ENABLE_MSG_SPLIT:
        # 提取后去除所有扩展调用指令并切分信息，剩余部分为对话结果 多行匹配
        talk_res = re.sub(r"/.?#(.+?)#.?/", "*;", talk_res)
        reply_list = talk_res.split("*;")
    else:
        # 提取后去除所有扩展调用指令，剩余部分为对话结果 多行匹配
        talk_res = re.sub(r"/.?#(.+?)#.?/", "", talk_res)
        reply_list.append(talk_res)

    # if config.DEBUG_LEVEL > 0: logger.info("分割响应结果: " + str(reply_list))

    # 重置所有扩展调用次数
    for ext_name in global_extensions.keys():
        global_extensions[ext_name].reset_call_times()

    # 遍历所有扩展调用指令
    for ext_call_str in ext_calls:
        ext_name, *ext_args = ext_call_str.split("&")
        ext_name = ext_name.strip().lower()
        if ext_name in global_extensions.keys():
            # 提取出扩展调用指令中的参数为字典
            ext_args_dict: dict = {}
            # 按照参数顺序依次提取参数值
            for arg_name in (
                global_extensions[ext_name].get_config().get("arguments").keys()
            ):
                if len(ext_args) > 0:
                    ext_args_dict[arg_name] = ext_args.pop(0)
                else:
                    ext_args_dict[arg_name] = None

            logger.info(f"检测到扩展调用指令: {ext_name} {ext_args_dict} | 正在调用扩展模块...")
            try:  # 调用扩展的call方法
                ext_res: dict = await global_extensions[ext_name].call(
                    ext_args_dict,
                    {
                        "bot_name": chat.get_chat_preset_key(),
                        "user_send_raw_text": trigger_text,
                        "bot_send_raw_text": raw_res,
                    },
                )
                if config.DEBUG_LEVEL > 0:
                    logger.info(f"扩展 {ext_name} 返回结果: {ext_res}")
                if ext_res is not None:
                    # 将扩展返回的结果插入到回复列表的最后
                    reply_list.append(ext_res)
            except Exception as e:
                logger.error(f"调用扩展 {ext_name} 时发生错误: {e}")
                if config.DEBUG_LEVEL > 0:
                    logger.error(f"[扩展 {ext_name}] 错误详情: {traceback.format_exc()}")
                ext_res = None
                # 将错误的调用指令从原始回复中去除，避免bot从上下文中学习到错误的指令用法
                raw_res = re.sub(r"/.?#(.+?)#.?/", "", raw_res)
        else:
            logger.error(f"未找到扩展 {ext_name}，跳过调用...")
            # 将错误的调用指令从原始回复中去除，避免bot从上下文中学习到错误的指令用法
            raw_res = re.sub(r"/.?#(.+?)#.?/", "", raw_res)

    # # 代码块插入到回复列表的最后
    # for code_block in code_blocks:
    #     reply_list.append({'code_block': code_block})

    if config.DEBUG_LEVEL > 0:
        logger.info(f"回复序列内容: {reply_list}")

    res_times = config.NG_MAX_RESPONSE_PER_MSG  # 获取每条消息最大回复次数
    # 根据回复内容列表逐条发送回复
    for idx, reply in enumerate(reply_list):
        # 判断回复内容是否为str
        if isinstance(reply, str) and reply.strip():
            # 判断文本内容是否为纯符号(包括空格，换行、英文标点、中文标点)并且长度小于3
            if re.match(r"^[^\u4e00-\u9fa5\w]{1}$", reply.strip()):
                if config.DEBUG_LEVEL > 0:
                    logger.info(f"检测到纯符号文本: {reply.strip()}，跳过发送...")
                continue
            if config.ENABLE_MSG_TO_IMG:
                img = await text_to_pic(reply.strip())
                await matcher.send(MessageSegment.image(img))
            else:
                await matcher.send(reply.strip())
        else:
            for key in reply:  # 遍历回复内容类型字典
                if key == "text" and reply.get(key) and reply.get(key).strip():  # 发送文本
                    # 判断文本内容是否为纯符号(包括空格，换行、英文标点、中文标点)并且长度为1
                    if re.match(r"^[^\u4e00-\u9fa5\w]{1}$", reply.get(key).strip()):
                        if config.DEBUG_LEVEL > 0:
                            logger.info(f"检测到纯符号文本: {reply.get(key).strip()}，跳过发送...")
                        continue
                    await matcher.send(reply.get(key).strip())
                    logger.info(f"回复文本消息: {reply.get(key).strip()}")
                elif key == "image" and reply.get(key):  # 发送图片
                    await matcher.send(MessageSegment.image(file=reply.get(key, "")))
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
                    chat.set_memory(
                        reply.get(key).get("key"), reply.get(key).get("value")
                    )
                    if config.DEBUG_LEVEL > 0:
                        if reply.get(key).get("key") and reply.get(key).get("value"):
                            await matcher.send(
                                f"[debug]: 记住了 {reply.get(key).get('key')} = {reply.get(key).get('value')}"
                            )
                        elif (
                            reply.get(key).get("key")
                            and reply.get(key).get("value") is None
                        ):
                            await matcher.send(
                                f"[debug]: 忘记了 {reply.get(key).get('key')}"
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
                elif key == "preset" and reply.get(key):  # 更新对话预设
                    if chat.update_preset(
                        preset_key=chat.preset_key, bot_self_introl=reply.get(key)
                    )[0]:
                        logger.info(f"更新对话预设: {reply.get(key)} 成功")
                    else:
                        logger.warning(f"更新对话预设: {reply.get(key)} 失败")

                res_times -= 1
                if res_times < 1:  # 如果回复次数超过限制，则跳出循环
                    break
        await asyncio.sleep(1.5)  # 每条回复之间间隔1.5秒

    cost_token = tg.cal_token_count(str(prompt_template) + raw_res)  # 计算对话结果的 token 数量

    while time.time() - sta_time < 1.5:  # 限制对话响应时间
        time.sleep(0.1)

    if config.DEBUG_LEVEL > 0:
        logger.info(f'token消耗: {cost_token} | 对话响应: "{raw_res}"')
    await chat.update_chat_history_row(
        sender=chat.get_chat_preset_key(), msg=raw_res, require_summary=True
    )  # 更新全局对话历史记录
    # 更新对用户的对话信息
    await chat.update_chat_history_row_for_user(
        sender=chat.get_chat_preset_key(),
        msg=raw_res,
        userid=trigger_userid,
        username=sender_name,
        require_summary=True,
    )
    PersistentDataManager.instance.save_to_file()  # 保存数据
    if config.DEBUG_LEVEL > 0:
        logger.info(f"对话响应完成 | 耗时: {time.time() - sta_time}s")

    # 检查是否再次触发对话
    if wake_up and loop_times < 3:
        if (
            "timer" in loop_data and "notify" in loop_data
        ):  # 如果存在定时器和通知消息，将其作为触发消息再次调用对话
            time_diff = loop_data["timer"]
            if time_diff > 0:
                if config.DEBUG_LEVEL > 0:
                    logger.info(f"等待 {time_diff}s 后再次调用对话...")
                await asyncio.sleep(time_diff)
            if config.DEBUG_LEVEL > 0:
                logger.info(f"再次调用对话...")
            await do_msg_response(
                matcher=matcher,
                trigger_text=loop_data.get("notify", {}).get("msg", ""),
                trigger_userid=trigger_userid,
                sender_name=loop_data.get("notify", {}).get("sender", "[system]"),
                wake_up=wake_up,
                loop_times=loop_times + 1,
                chat_type="group",
                is_tome=is_tome,
                chat_key=chat_key,
            )
        elif "notify" in loop_data:  # 如果存在通知消息，将其作为触发消息再次调用对话
            await do_msg_response(
                matcher=matcher,
                trigger_text=loop_data.get("notify", {}).get("msg", ""),
                trigger_userid=trigger_userid,
                sender_name=loop_data.get("notify", {}).get("sender", "[system]"),
                wake_up=wake_up,
                loop_times=loop_times + 1,
                chat_type="group",
                is_tome=is_tome,
                chat_key=chat_key,
            )
