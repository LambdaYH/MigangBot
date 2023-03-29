from pathlib import Path

import nonebot

__plugin_hidden__ = True

nonebot.load_plugins(str(Path(__file__).parent.resolve()))
