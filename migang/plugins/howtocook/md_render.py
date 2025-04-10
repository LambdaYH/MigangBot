# 为了给md_to_text应用代理，只能抄过来改一下
from os import getcwd
from typing import Union, Literal, Optional

import markdown
from nonebot import require
from nonebot.log import logger

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender.browser import get_new_page
from nonebot_plugin_htmlrender.data_source import (
    TEMPLATES_PATH,
    env,
    read_tpl,
    read_file,
)

from migang.core.utils import http_utils


async def handle_route(route):
    headers = {**route.request.headers, **http_utils.get_gh_headers()}
    await route.continue_(headers=headers)


async def md_to_pic(
    md: str = "",
    md_path: str = "",
    css_path: str = "",
    width: int = 500,
    type: Literal["jpeg", "png"] = "png",  # noqa: A002
    quality: Union[int, None] = None,
    device_scale_factor: float = 2,
    screenshot_timeout: Optional[float] = 30_000,
) -> bytes:
    """markdown 转 图片

    Args:
        screenshot_timeout (float, optional): 截图超时时间，默认30000ms
        md (str, optional): markdown 格式文本
        md_path (str, optional): markdown 文件路径
        css_path (str,  optional): css文件路径. Defaults to None.
        width (int, optional): 图片宽度，默认为 500
        type (Literal["jpeg", "png"]): 图片类型, 默认 png
        quality (int, optional): 图片质量 0-100 当为`png`时无效
        device_scale_factor: 缩放比例,类型为float,值越大越清晰(真正想让图片清晰更优先请调整此选项)

    Returns:
        bytes: 图片, 可直接发送
    """
    template = env.get_template("markdown.html")
    if not md:
        if md_path:
            md = await read_file(md_path)
        else:
            raise Exception("必须输入 md 或 md_path")
    logger.debug(md)
    md = markdown.markdown(
        md,
        extensions=[
            "pymdownx.tasklist",
            "tables",
            "fenced_code",
            "codehilite",
            "mdx_math",
            "pymdownx.tilde",
        ],
        extension_configs={"mdx_math": {"enable_dollar_delimiter": True}},
    )

    logger.debug(md)
    extra = ""
    if "math/tex" in md:
        katex_css = await read_tpl("katex/katex.min.b64_fonts.css")
        katex_js = await read_tpl("katex/katex.min.js")
        mhchem_js = await read_tpl("katex/mhchem.min.js")
        mathtex_js = await read_tpl("katex/mathtex-script-type.min.js")
        extra = (
            f'<style type="text/css">{katex_css}</style>'
            f"<script defer>{katex_js}</script>"
            f"<script defer>{mhchem_js}</script>"
            f"<script defer>{mathtex_js}</script>"
        )

    if css_path:
        css = await read_file(css_path)
    else:
        css = await read_tpl("github-markdown-light.css") + await read_tpl(
            "pygments-default.css",
        )

    return await html_to_pic(
        template_path=f"file://{css_path if css_path else TEMPLATES_PATH}",
        html=await template.render_async(md=md, css=css, extra=extra),
        viewport={"width": width, "height": 10},
        type=type,
        quality=quality,
        device_scale_factor=device_scale_factor,
        screenshot_timeout=screenshot_timeout,
    )


async def html_to_pic(
    html: str,
    wait: int = 0,
    template_path: str = f"file://{getcwd()}",  # noqa: PTH109
    type: Literal["jpeg", "png"] = "png",  # noqa: A002
    quality: Union[int, None] = None,
    device_scale_factor: float = 2,
    screenshot_timeout: Optional[float] = 30_000,
    **kwargs,
) -> bytes:
    """html转图片

    Args:
        screenshot_timeout (float, optional): 截图超时时间，默认30000ms
        html (str): html文本
        wait (int, optional): 等待时间. Defaults to 0.
        template_path (str, optional): 模板路径 如 "file:///path/to/template/"
        type (Literal["jpeg", "png"]): 图片类型, 默认 png
        quality (int, optional): 图片质量 0-100 当为`png`时无效
        device_scale_factor: 缩放比例,类型为float,值越大越清晰(真正想让图片清晰更优先请调整此选项)
        **kwargs: 传入 page 的参数

    Returns:
        bytes: 图片, 可直接发送
    """
    # logger.debug(f"html:\n{html}")
    if "file:" not in template_path:
        raise Exception("template_path 应该为 file:///path/to/template")
    async with get_new_page(device_scale_factor, **kwargs) as page:
        await page.route("**/raw.githubusercontent.com/**", handle_route)
        page.on("console", lambda msg: logger.debug(f"浏览器控制台: {msg.text}"))
        await page.goto(template_path)
        await page.set_content(html, wait_until="networkidle")
        await page.wait_for_timeout(wait)
        return await page.screenshot(
            full_page=True,
            type=type,
            quality=quality,
            timeout=screenshot_timeout,
        )
