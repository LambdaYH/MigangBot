from pathlib import Path
from typing import Dict, List

from nonebot_plugin_htmlrender import template_to_pic

template_path = Path(__file__).parent / "templates"


async def render_music_list(
    music_list: List[Dict], multi_source: bool = False
) -> bytes:
    return await template_to_pic(
        template_path=template_path,
        template_name="music_list.html",
        pages={
            "viewport": {"width": 720, "height": 200},
        },
        templates={"music_list": music_list, "multi_source": multi_source},
    )
