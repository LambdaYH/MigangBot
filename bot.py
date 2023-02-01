import nonebot
from nonebot.adapters.onebot.v11 import Adapter

from migangbot.core.manager import count_manager


nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(Adapter)
config = driver.config

driver.on_shutdown(count_manager.Save)

# core
nonebot.load_plugin("nonebot_plugin_apscheduler")
nonebot.load_plugin("nonebot_plugin_htmlrender")
nonebot.load_plugin("nonebot_plugin_imageutils")
nonebot.load_plugins("migangbot/core/core_plugins")

# plugins
nonebot.load_plugins("migangbot/plugins")

if __name__ == "__main__":
    nonebot.run()
