import nonebot
from nonebot.adapters.onebot.v11 import Adapter
from tortoise import Tortoise

from migangbot.core.manager import save
from migangbot.core.database import init_db


nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(Adapter)
config = driver.config
# driver.on_startup(init_db)
# driver.on_shutdown(Tortoise.close_connections())
driver.on_shutdown(save)

# core
nonebot.load_plugin("nonebot_plugin_apscheduler")
nonebot.load_plugin("nonebot_plugin_htmlrender")
nonebot.load_plugin("nonebot_plugin_imageutils")
nonebot.load_plugins("migangbot/core/core_plugins")

# plugins
nonebot.load_plugins("migangbot/plugins")

if __name__ == "__main__":
    nonebot.run()
