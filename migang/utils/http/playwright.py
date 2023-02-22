from pathlib import Path
from typing import Dict, List, Union, Literal, Optional

from nonebot.log import logger
from nonebot_plugin_htmlrender import get_new_page


# zhenxun_bot
async def screenshot(
    url: str,
    path: Union[Path, str, None],
    element: Union[str, List[str]],
    *,
    wait_time: Optional[int] = None,
    viewport_size: Dict[str, int] = None,
    wait_until: Optional[
        Literal["domcontentloaded", "load", "networkidle"]
    ] = "networkidle",
    timeout: float = None,
    type_: Literal["jpeg", "png"] = None,
    **kwargs,
) -> Optional[bytes]:
    """截图，该方法仅用于简单快捷截图，复杂截图请操作 page

    Args:
        url (str): 网址
        path (Union[Path, str, None]): 存储路径
        element (Union[str, List[str]]): 元素选择
        wait_time (Optional[int], optional): 等待截取超时时间. Defaults to None.
        viewport_size (Dict[str, int], optional): 窗口大小. Defaults to None.
        wait_until: 等待类型. Defaults to "networkidle".
        timeout (float, optional): 超时限制. Defaults to None.
        type_ : 保存类型. Defaults to None.

    Returns:
        Optional[bytes]: 图片
    """
    if viewport_size is None:
        viewport_size = dict(width=2560, height=1080)
    if isinstance(path, str):
        path = Path(path)
    try:
        async with get_new_page(viewport=viewport_size) as page:
            page = await page.goto(url, wait_until=wait_until, **kwargs)
            if isinstance(element, str):
                if wait_time:
                    card = await page.wait_for_selector(
                        element, timeout=wait_time * 1000
                    )
                else:
                    card = await page.query_selector(element)
            else:
                card = page
                for e in element:
                    if wait_time:
                        card = await card.wait_for_selector(e, timeout=wait_time * 1000)
                    else:
                        card = await card.query_selector(e)
            return await card.screenshot(path=path, timeout=timeout, type=type_)
    except Exception as e:
        logger.warning(f"Playwright 截图 url：{url} element：{element} 发生错误 {type(e)}：{e}")
    return None
