﻿import os
import re
import time
import random
import asyncio
import difflib
import traceback
from typing import Set, Dict, List, Tuple, Callable, Optional, Awaitable

from nonebot.log import logger
from nonebot.params import Event, Matcher, CommandArg
from nonebot import on_notice, get_driver, on_command, on_message
from nonebot.adapters.onebot.v11 import (
    Bot,
    Message,
    MessageEvent,
    MessageSegment,
    GroupMessageEvent,
    PrivateMessageEvent,
    GroupIncreaseNoticeEvent,
)

from .utils import *
from .config import *
from .chat import Chat
from .chat_manager import ChatManager
from .openai_func import TextGenerator
from .Extension import Extension, global_extensions
from .persistent_data_manager import PersistentDataManager

try:
    import nonebot_plugin_htmlrender

    from .text_func import text_to_img
except:
    config.ENABLE_MSG_TO_IMG = False
    config.ENABLE_COMMAND_TO_IMG = False

permission_check_func: Callable[
    [Matcher, MessageEvent, Bot, str, str], Awaitable[Tuple[bool, str]]
] = None
is_progress: bool = False

msg_sent_set: Set[str] = set()  # bot 自己发送的消息

"""消息发送钩子，用于记录自己发送的消息(默认不开启，只有在用户自定义了message_sent事件之后message_sent事件才会被发送到 on_message 回调)"""


# @Bot.on_called_api
async def handle_group_message_sent(
    bot: Bot,
    exception: Optional[Exception],
    api: str,
    data: Dict[str, Any],
    result: Any,
):
    global msg_sent_set
    if result and (api in ["send_msg", "send_group_msg", "send_private_msg"]):
        msg_id = result.get("message_id", None)
        if msg_id:
            msg_sent_set.add(f"{bot.self_id}_{msg_id}")


""" ======== 注册消息响应器 ======== """


# 注册消息响应器 收到任意消息时触发
# matcher:Matcher = on_message(priority=config.NG_MSG_PRIORITY, block=config.NG_BLOCK_OTHERS)
# @matcher.handle()
async def handler(matcher_: Matcher, event: MessageEvent, bot: Bot) -> None:
    global msg_sent_set
    if event.post_type == "message_sent":  # 通过bot.send发送的消息不处理
        msg_key = f"{bot.self_id}_{event.message_id}"
        if msg_key in msg_sent_set:
            msg_sent_set.remove(msg_key)
            return

    if len(msg_sent_set) > 10:
        if config.DEBUG_LEVEL > 0:
            logger.warning(f"累积的待处理的自己发送消息数量为 {len(msg_sent_set)}, 请检查逻辑是否有错误")
        msg_sent_set.clear()

    # # 处理消息前先检查权限
    # (permit_success, _) = await permission_check_func(matcher=matcher_, event=event, bot=bot, cmd=None, type='message')
    # if not permit_success:
    #     return

    # 判断用户账号是否被屏蔽
    if event.get_user_id() in config.FORBIDDEN_USERS:
        if config.DEBUG_LEVEL > 0:
            logger.info(f"用户 {event.get_user_id()} 被屏蔽，拒绝处理消息")
        return

    sender_name = (
        await get_user_name(event=event, bot=bot, user_id=event.user_id) or "未知"
    )

    resTmplate = (  # 测试用，获取消息的相关信息
        f"收到消息: {event.get_message()}"
        f"\n消息名称: {event.get_event_name()}"
        f"\n消息描述: {event.get_event_description()}"
        f"\n消息来源: {event.get_session_id()}"
        f"\n消息文本: {event.get_plaintext()}"
        f"\n消息主体: {event.get_user_id()}"
        f"\n消息内容: {event.get_message()}"
        f"\n发送者: {sender_name}"
        f"\n是否to-me: {event.is_tome()}"
        # f"\nJSON: {event.json()}"
    )
    if config.DEBUG_LEVEL > 1:
        logger.info(resTmplate)

    # 如果是忽略前缀 或者 消息为空，则跳过处理
    if (
        event.get_plaintext().strip().startswith(config.IGNORE_PREFIX)
        or not event.get_plaintext()
    ):
        if config.DEBUG_LEVEL > 1:
            logger.info("忽略前缀或消息为空，跳过处理...")  # 纯图片消息也会被判定为空消息
        return

    # 判断群聊/私聊
    if isinstance(event, GroupMessageEvent):
        chat_key = "group_" + event.get_session_id().split("_")[1]
        chat_type = "group"
    elif isinstance(event, PrivateMessageEvent):
        chat_key = "private_" + event.get_user_id()
        chat_type = "private"
    else:
        if config.DEBUG_LEVEL > 0:
            logger.info("未知消息来源: " + event.get_session_id())
        return

    chat_text, wake_up = await gen_chat_text(event=event, bot=bot)

    # 进行消息响应
    await do_msg_response(
        event.get_user_id(),
        chat_text,
        event.is_tome() or wake_up,
        matcher_,
        chat_type,
        chat_key,
        sender_name,
    )


""" ======== 消息响应方法 ======== """


async def do_msg_response(
    trigger_userid: str,
    trigger_text: str,
    is_tome: bool,
    matcher: Matcher,
    chat_type: str,
    chat_key: str,
    sender_name: str = None,
    wake_up: bool = False,
    loop_times=0,
    loop_data={},
):
    """消息响应方法"""

    chat: Chat = ChatManager.instance.get_or_create_chat(chat_key=chat_key)

    # # 判断对话是否被禁用
    # if not chat.is_enable:
    #     if config.DEBUG_LEVEL > 1: logger.info("对话已被禁用，跳过处理...")
    #     return

    # 检测是否包含违禁词
    for w in config.WORD_FOR_FORBIDDEN:
        if str(w).lower() in trigger_text.lower():
            if config.DEBUG_LEVEL > 0:
                logger.info(f"检测到违禁词 {w}，拒绝处理...")
            return

    # 唤醒词检测
    for w in config.WORD_FOR_WAKE_UP:
        if str(w).lower() in trigger_text.lower():
            wake_up = True
            break

    # 随机回复判断
    if random.random() < config.RANDOM_CHAT_PROBABILITY:
        wake_up = True

    # # 其它人格唤醒判断
    # if chat.get_chat_preset_key().lower() not in trigger_text.lower() and chat.enable_auto_switch_identity:
    #     for preset_key in chat.preset_keys:
    #         if preset_key.lower() in trigger_text.lower():
    #             chat.change_presettings(preset_key)
    #             logger.info(f"检测到 {preset_key} 的唤醒词，切换到 {preset_key} 的人格")
    #             await matcher.send(f'[NG] 已切换到 {preset_key} (￣▽￣)-ok !')
    #             wake_up = True
    #             break

    # current_preset_key = chat.get_chat_preset_key()

    # 判断是否需要回复
    if (  # 如果不是 bot 相关的信息，则直接返回
        wake_up
        or (
            config.REPLY_ON_NAME_MENTION
            and (chat.get_chat_preset_key().lower() in trigger_text.lower())
        )
        or (config.REPLY_ON_AT and is_tome)
    ):
        # 更新全局对话历史记录
        # chat.update_chat_history_row(sender=sender_name, msg=trigger_text, require_summary=True)
        await chat.update_chat_history_row(
            sender=sender_name,
            msg=f"@{chat.get_chat_preset_key()} {trigger_text}"
            if is_tome and chat_type == "group"
            else trigger_text,
            require_summary=False,
        )
        logger.info("符合 bot 发言条件，进行回复...")
    else:
        if config.CHAT_ENABLE_RECORD_ORTHER:
            await chat.update_chat_history_row(
                sender=sender_name, msg=trigger_text, require_summary=False
            )
            if config.DEBUG_LEVEL > 1:
                logger.info("不是 bot 相关的信息，记录但不进行回复")
        else:
            if config.DEBUG_LEVEL > 1:
                logger.info("不是 bot 相关的信息，不进行回复")
        return

    wake_up = False  # 进入对话流程，重置唤醒状态

    # 记录对用户的对话信息
    await chat.update_chat_history_row_for_user(
        sender=sender_name,
        msg=trigger_text,
        userid=trigger_userid,
        username=sender_name,
        require_summary=False,
    )

    # if chat.get_chat_preset_key() != current_preset_key:
    #     logger.warning(f'等待OpenAI请求返回的过程中人格预设由[{current_preset_key}]切换为[{chat.get_chat_preset_key()}],当前消息不再继续响应.1')
    #     return

    # 主动聊天参与逻辑 *待定方案
    # 达到一定兴趣阈值后，开始进行一次启动发言准备 收集特定条数的对话历史作为发言参考
    # 启动发言后，一段时间内兴趣值逐渐下降，如果随后被呼叫，则兴趣值提升
    # 监测对话历史中是否有足够的话题参与度，如果有，则继续提高话题参与度，否则，降低话题参与度
    # 兴趣值影响发言频率，兴趣值越高，发言频率越高
    # 如果监测到对话记录中有不满情绪(如: 闭嘴、滚、不理你、安静等)，则大幅降低兴趣值并且降低发言频率，同时进入一段时间的沉默期(0-120分钟)
    # 沉默期中降低响应"提及"的概率，沉默期中被直接at，则恢复一定兴趣值提升兴趣值并取消沉默期
    # 兴趣值会影响回复的速度，兴趣值越高，回复速度越快
    # 发言概率贡献比例 = (随机值: 10% + 话题参与度: 50% + 兴趣值: 40%) * 发言几率基数(0.01~1.0)

    sta_time: float = time.time()

    # 生成对话 prompt 模板
    prompt_template = chat.get_chat_prompt_template(userid=trigger_userid)
    # 生成 log 输出用的 prompt 模板
    log_prompt_template = (
        "\n".join([f"[{m['role']}]\n{m['content']}\n" for m in prompt_template])
        if isinstance(prompt_template, list)
        else prompt_template
    )
    if config.DEBUG_LEVEL > 0:
        # logger.info("对话 prompt 模板: \n" + str(log_prompt_template))
        # 保存 prompt 模板到日志文件
        with open(
            os.path.join(
                config.NG_LOG_PATH,
                f"{chat_key}.{time.strftime('%Y-%m-%d %H-%M-%S')}.prompt.log",
            ),
            "a",
            encoding="utf-8",
        ) as f:
            f.write(f"prompt 模板: \n{log_prompt_template}\n")
        logger.info(
            f"对话 prompt 模板已保存到日志文件: {chat_key}.{time.strftime('%Y-%m-%d %H-%M-%S')}.prompt.log"
        )

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

    # if chat.get_chat_preset_key() != current_preset_key:
    #     logger.warning(f'等待OpenAI响应返回的过程中人格预设由[{current_preset_key}]切换为[{chat.get_chat_preset_key()}],当前消息不再继续处理.2')
    #     return

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

    # 提取markdown格式的代码块
    code_blocks = re.findall(r"```(.+?)```", raw_res, re.S)
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
                img = await text_to_img(reply.strip())
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
                chat_type=chat_type,
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
                chat_type=chat_type,
                is_tome=is_tome,
                chat_key=chat_key,
            )
