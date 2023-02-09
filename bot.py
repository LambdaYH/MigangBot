import nonebot
from nonebot.adapters.onebot.v11 import Adapter

from migang.core.manager import save
from migang.core.database import init_db, close_db


nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(Adapter)
config = driver.config
driver.on_startup(init_db)
driver.on_shutdown(close_db)
driver.on_shutdown(save)

# core
nonebot.load_plugin("nonebot_plugin_apscheduler")
nonebot.load_plugin("nonebot_plugin_htmlrender")
nonebot.load_plugin("nonebot_plugin_imageutils")
nonebot.load_plugins("migang/core/core_plugins")

# plugins
nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    nonebot.run()
