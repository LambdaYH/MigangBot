from nonebot.plugin import get_loaded_plugins


_ignore_plugin = set(
    [
        "nonebot_plugin_imageutils",
        "nonebot_plugin_apscheduler",
        "nonebot_plugin_htmlrender",
    ]
)


def GetPluginList():
    plugins = get_loaded_plugins()
    return [
        plugin
        for plugin in plugins
        if (not plugin.module_name.startswith("migangbot.core"))
        and (plugin.name not in _ignore_plugin)
    ]
