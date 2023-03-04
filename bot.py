import nonebot
from nonebot.adapters.onebot.v11 import Adapter

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(Adapter)
config = driver.config

# core
nonebot.load_plugin("nonebot_plugin_apscheduler")
nonebot.load_plugin("nonebot_plugin_htmlrender")
nonebot.load_plugin("nonebot_plugin_imageutils")
nonebot.load_plugin("nonebot_plugin_datastore")
nonebot.load_plugins("migang/core/core_plugins")

# plugins
nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    nonebot.run()
