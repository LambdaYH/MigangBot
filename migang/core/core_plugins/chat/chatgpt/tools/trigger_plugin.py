from nonebot.matcher import current_bot, current_event
from nonebot.adapters.onebot.v11 import Message, MessageSegment, GroupMessageEvent

from migang.core.utils.langchain_tool import nb_langchain_tool


@nb_langchain_tool
async def trigger_plugin(content: str):
    """
    触发插件，通过输入指令实现插件的触发

    Args:
        content (str): 触发插件的完整指令
    """
    if not content:
        return "请输入插件指令"
    bot = current_bot.get()
    event = current_event.get()
    if not bot or not event:
        return "无法获取当前bot或event，无法触发插件。"
    # 拼接at
    if isinstance(event, GroupMessageEvent):
        at_msg = MessageSegment.at(event.self_id) + Message(content)
    else:
        at_msg = Message(content)
    # 构造新事件（复用原event，替换message）
    new_event = event.model_copy()
    new_event.message = at_msg
    new_event.original_message = at_msg
    new_event.raw_message = str(at_msg)
    # 标记为llm触发
    setattr(new_event, "llm_trigger", True)
    try:
        await bot.handle_event(new_event)
        return "插件已触发，结果已直接发送给用户"
    except Exception as e:
        return f"插件触发失败: {e}"
