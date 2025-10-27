import asyncio
import smtplib
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText
from typing import Any, Dict, List, Tuple, Union, Sequence

import httpx
from nonebot.log import logger
from nonebot import on_notice, get_driver
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Bot, NoticeEvent

from migang.core import ConfigItem, get_config

SUBJECT_TEMPLATE_DEFAULT = "机器人 {bot_id} 离线"
BODY_TEMPLATE_DEFAULT = "机器人 {bot_id} 已离线\n标签: {tag}\n消息: {message}\n时间: {time}"

__plugin_meta__ = PluginMetadata(
    name="机器人离线通知",
    description="监听机器人离线事件并通过配置的渠道发送提醒",
    usage="配置好 Bark、SMTP 或 Gotify 后自动发送通知",
    type="application",
    supported_adapters={"~onebot.v11"},
)

__plugin_always_on__ = True
__plugin_hidden__ = True
__plugin_category__ = "基础功能"

__plugin_config__ = (
    ConfigItem(
        key="subject_template",
        initial_value=SUBJECT_TEMPLATE_DEFAULT,
        default_value=SUBJECT_TEMPLATE_DEFAULT,
        description="通知标题模板，可用变量: bot_id, self_id, tag, message, time, timestamp",
    ),
    ConfigItem(
        key="body_template",
        initial_value=BODY_TEMPLATE_DEFAULT,
        default_value=BODY_TEMPLATE_DEFAULT,
        description="通知正文模板，可用变量: bot_id, self_id, tag, message, time, timestamp",
    ),
    ConfigItem(
        key="bark",
        initial_value={
            "enabled": False,
            "server": "https://api.day.app",
            "device_key": "",
            "group": "",
            "sound": "",
            "icon": "",
            "url": "",
        },
        default_value={},
        description="Bark 推送配置",
    ),
    ConfigItem(
        key="smtp",
        initial_value={
            "enabled": False,
            "host": "",
            "port": 465,
            "username": "",
            "password": "",
            "from_addr": "",
            "to": [],
            "use_ssl": True,
            "use_tls": False,
        },
        default_value={},
        description="SMTP 邮件配置，to 支持列表或逗号分隔字符串",
    ),
    ConfigItem(
        key="gotify",
        initial_value={
            "enabled": False,
            "endpoint": "",
            "token": "",
            "priority": 5,
        },
        default_value={},
        description="Gotify 推送配置",
    ),
)


def _render_template(template: Any, context: Dict[str, Any], fallback: str) -> str:
    if not isinstance(template, str) or not template:
        return fallback
    try:
        return template.format(**context)
    except KeyError as exc:
        logger.warning("offline_notification: 模板缺少字段 %s", exc)
        return fallback


def _normalize_recipients(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [addr.strip() for addr in value.split(",") if addr.strip()]
    if isinstance(value, (list, tuple, set)):
        result: List[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                result.append(text)
        return result
    text = str(value).strip()
    return [text] if text else []


def _build_context_from_notice(event: NoticeEvent) -> Dict[str, Any]:
    bot_id = getattr(event, "user_id", None) or event.self_id
    tag = getattr(event, "tag", "")
    message = getattr(event, "message", "")
    timestamp = getattr(event, "time", 0)
    time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    return {
        "bot_id": str(bot_id),
        "self_id": str(event.self_id),
        "tag": str(tag),
        "message": str(message),
        "timestamp": timestamp,
        "time": time_str,
    }


def _build_context_from_bot(bot: Bot) -> Dict[str, Any]:
    timestamp = int(datetime.now().timestamp())
    time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    bot_id = getattr(bot, "self_id", None) or getattr(bot, "bot_id", None) or "unknown"
    return {
        "bot_id": str(bot_id),
        "self_id": str(getattr(bot, "self_id", bot_id)),
        "tag": "driver",
        "message": "驱动断开连接",
        "timestamp": timestamp,
        "time": time_str,
    }


async def _send_bark(config: Dict[str, Any], title: str, body: str) -> None:
    if not config.get("enabled"):
        return
    server = str(config.get("server") or "https://api.day.app").rstrip("/")
    device_key = config.get("device_key") or config.get("key")
    if not device_key:
        raise ValueError("Bark device_key 未配置")
    payload = {"title": title, "body": body, "device_key": device_key}
    for optional in ("group", "sound", "icon", "url"):
        value = config.get(optional)
        if value:
            payload[optional] = value
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(f"{server}/push", json=payload)
        response.raise_for_status()


async def _send_gotify(config: Dict[str, Any], title: str, body: str) -> None:
    if not config.get("enabled"):
        return
    endpoint = config.get("endpoint") or config.get("server")
    token = config.get("token")
    if not endpoint or not token:
        raise ValueError("Gotify endpoint 或 token 未配置")
    url = str(endpoint).rstrip("/") + "/message"
    payload = {
        "title": title,
        "message": body,
        "priority": int(config.get("priority", 5)),
    }
    headers = {"X-Gotify-Key": token}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()


async def _send_smtp(config: Dict[str, Any], subject: str, body: str) -> None:
    if not config.get("enabled"):
        return
    host = config.get("host")
    recipients = _normalize_recipients(config.get("to"))
    if not host or not recipients:
        raise ValueError("SMTP host 或收件人未配置")
    port = int(config.get("port") or 465)
    username = config.get("username") or config.get("user")
    password = config.get("password")
    from_addr = config.get("from_addr") or username
    if not from_addr:
        raise ValueError("SMTP from_addr 未配置")
    use_ssl = bool(config.get("use_ssl", True))
    use_tls = bool(config.get("use_tls", False))
    await asyncio.to_thread(
        _send_mail_sync,
        host,
        port,
        use_ssl,
        use_tls,
        username,
        password,
        from_addr,
        recipients,
        subject,
        body,
    )


def _send_mail_sync(
    host: str,
    port: int,
    use_ssl: bool,
    use_tls: bool,
    username: Union[str, None],
    password: Union[str, None],
    from_addr: str,
    recipients: Sequence[str],
    subject: str,
    body: str,
) -> None:
    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = Header(subject, "utf-8")
    message["From"] = from_addr
    message["To"] = ", ".join(recipients)
    if use_ssl:
        server: smtplib.SMTP = smtplib.SMTP_SSL(host, port)
    else:
        server = smtplib.SMTP(host, port)
    try:
        server.ehlo()
        if not use_ssl and use_tls:
            server.starttls()
            server.ehlo()
        if username and password:
            server.login(username, password)
        server.sendmail(from_addr, list(recipients), message.as_string())
    finally:
        try:
            server.quit()
        except Exception:
            server.close()


def _notice_rule(event: NoticeEvent) -> bool:
    return event.notice_type == "bot_offline"


async def _dispatch_notifications(context: Dict[str, Any]) -> None:
    subject_template = await get_config("subject_template")
    body_template = await get_config("body_template")
    subject = _render_template(
        subject_template, context, SUBJECT_TEMPLATE_DEFAULT.format(**context)
    )
    body = _render_template(
        body_template,
        context,
        BODY_TEMPLATE_DEFAULT.format(**context),
    )

    bark_config = await get_config("bark") or {}
    smtp_config = await get_config("smtp") or {}
    gotify_config = await get_config("gotify") or {}

    channel_coroutines: List[Tuple[str, Any]] = []
    if isinstance(bark_config, dict) and bark_config.get("enabled"):
        channel_coroutines.append(("bark", _send_bark(bark_config, subject, body)))
    if isinstance(smtp_config, dict) and smtp_config.get("enabled"):
        channel_coroutines.append(("smtp", _send_smtp(smtp_config, subject, body)))
    if isinstance(gotify_config, dict) and gotify_config.get("enabled"):
        channel_coroutines.append(
            ("gotify", _send_gotify(gotify_config, subject, body))
        )

    if not channel_coroutines:
        logger.warning("offline_notification: 触发机器人离线事件但未启用任何通知渠道，已跳过发送")
        return

    results = await asyncio.gather(
        *(coro for _, coro in channel_coroutines), return_exceptions=True
    )
    for (name, _), result in zip(channel_coroutines, results):
        if isinstance(result, Exception):
            logger.error(f"offline_notification: {name} 通知发送失败: {result}")
        else:
            logger.info(f"offline_notification: {name} 通知已发送")


driver = get_driver()

offline_notice = on_notice(priority=1, block=False, rule=_notice_rule)


@offline_notice.handle()
async def _(event: NoticeEvent) -> None:
    context = _build_context_from_notice(event)
    await _dispatch_notifications(context)


@driver.on_bot_disconnect
async def _(bot: Bot) -> None:
    context = _build_context_from_bot(bot)
    await _dispatch_notifications(context)
