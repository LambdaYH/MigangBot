from matplotlib import font_manager
from migang.core import FONT_PATH
from pathlib import Path

from migang.core.utils.file_operation import async_load_data, async_save_data


async def load_font():
    import ujson as json

    # 一次性加载字体文件夹下的所有字体
    for font in font_manager.findSystemFonts((FONT_PATH,)):
        font_manager.fontManager.addfont(font)

    # 生成字体文件与字体名的索引，方便寻找
    font_index_path = FONT_PATH / "font_index.json"  # 字体文件和字体名的对应，方便找
    font_index = await async_load_data(font_index_path)
    for font in font_manager.fontManager.ttflist:
        font_path = Path(font.fname)
        if font_path.parent == FONT_PATH and font_path.name not in font_index:
            font_index[font_path.name] = font.name
    await async_save_data(font_index, font_index_path)
