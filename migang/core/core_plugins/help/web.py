from __future__ import annotations

"""基于 FastAPI 的帮助网页与临时 Token 校验"""

import uuid
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta

from nonebot import get_driver
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, HTMLResponse
from fastapi import Query, Request, APIRouter, HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape

from migang.core.manager import (
    PluginType,
    task_manager,
    user_manager,
    group_manager,
    plugin_manager,
)

from .data_source import (
    TEMPLATE_PATH,
    MenuItem,
    PluginStatus,
    _sort_data,
    get_plugin_help,
    get_help_menu_context,
)


class _TempToken:
    def __init__(self, payload: Dict, expires_at: datetime) -> None:
        self.payload = payload
        self.expires_at = expires_at

    def valid(self) -> bool:
        return datetime.utcnow() < self.expires_at


class HelpTokenManager:
    """简单的内存 Token 管理，默认 7 天过期"""

    def __init__(self) -> None:
        self._tokens: Dict[str, _TempToken] = {}

    def create(self, payload: Dict, ttl_minutes: int = 60 * 24 * 7) -> str:
        token = uuid.uuid4().hex
        self._tokens[token] = _TempToken(
            payload=payload,
            expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
        )
        return token

    def get(self, token: str) -> Optional[Dict]:
        data = self._tokens.get(token)
        if not data:
            return None
        if not data.valid():
            # 过期后清理
            self._tokens.pop(token, None)
            return None
        return data.payload

    def purge(self) -> None:
        now = datetime.utcnow()
        for t, v in list(self._tokens.items()):
            if v.expires_at <= now:
                self._tokens.pop(t, None)


token_manager = HelpTokenManager()


def create_help_token(
    *, group_id: Optional[int], user_id: Optional[int], super_user: bool
) -> str:
    """对外暴露的创建 Token 方法"""
    return token_manager.create(
        {
            "group_id": group_id,
            "user_id": user_id,
            "super_user": super_user,
        }
    )


# FastAPI 路由与模板
router = APIRouter()

_env = Environment(
    loader=FileSystemLoader(str(Path(TEMPLATE_PATH) / "web")),
    autoescape=select_autoescape(["html", "xml"]),
)


def _get_status_for_plugin(
    *, plugin, group_id: Optional[int], user_id: Optional[int], super_user: bool
) -> PluginStatus:
    status = PluginStatus.enabled
    if not plugin.global_status:
        return PluginStatus.group_disabled
    if group_id:
        if not group_manager.check_plugin_permission(
            plugin_name=plugin.plugin_name, group_id=group_id
        ):
            status = PluginStatus.not_authorized
        else:
            status = (
                PluginStatus.enabled
                if group_manager.check_group_plugin_status(
                    plugin_name=plugin.plugin_name, group_id=group_id
                )
                else PluginStatus.disabled
            )
    elif user_id:
        if not user_manager.check_plugin_permission(
            plugin_name=plugin.plugin_name, user_id=user_id
        ):
            status = PluginStatus.not_authorized
        else:
            status = (
                PluginStatus.enabled
                if user_manager.check_user_plugin_status(
                    plugin_name=plugin.plugin_name, user_id=user_id
                )
                else PluginStatus.disabled
            )
            type_block = {PluginType.Group, PluginType.GroupAdmin, PluginType.SuperUser}
            if super_user:
                type_block.remove(PluginType.SuperUser)
            if plugin.plugin_type in type_block:
                status = PluginStatus.disabled
    return status


@router.get("/help", response_class=HTMLResponse)
async def web_help(request: Request, t: str = Query(..., alias="t")):
    payload = token_manager.get(t)
    if not payload:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    _sort_data()
    ctx = get_help_menu_context(
        group_id=payload.get("group_id"),
        user_id=payload.get("user_id"),
        super_user=payload.get("super_user", False),
    )
    # 使用单独的网页模板
    template = Environment(
        loader=FileSystemLoader(str(Path(TEMPLATE_PATH) / "web_help")),
        autoescape=select_autoescape(["html", "xml"]),
    ).get_template("index.html")
    html = template.render(**ctx)
    return HTMLResponse(content=html)


@router.get("/help/plugin")
async def web_help_plugin(request: Request, name: str, t: str = Query(..., alias="t")):
    payload = token_manager.get(t)
    if not payload:
        raise HTTPException(status_code=401, detail="token 无效或已过期")

    # 使用方法（复用数据源方法）
    usage = get_plugin_help(name) or "暂无使用说明"
    if not usage:
        raise HTTPException(status_code=404, detail="插件不存在")

    # 单插件页：使用与聊天相同的渲染，返回 png 图片
    from .data_source import build_usage_png

    png = await build_usage_png(usage)
    if isinstance(png, BytesIO):
        png = png.getvalue()
    return Response(content=png, media_type="image/png")


@router.get("/help/plugin_usage")
async def web_help_plugin_usage(
    request: Request, name: str, t: str = Query(..., alias="t")
):
    payload = token_manager.get(t)
    if not payload:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    usage = get_plugin_help(name) or "暂无使用说明"
    return {"usage": usage}


# 将路由挂载到 nonebot 的 FastAPI 应用，并挂载静态文件
driver = get_driver()
app = getattr(driver, "server_app", None)
if app is not None:
    app.include_router(router)
    # 提供网页模板自己的静态资源
    app.mount(
        "/help/web_static",
        StaticFiles(directory=str(Path(TEMPLATE_PATH) / "web_help")),
        name="help_web_static",
    )
