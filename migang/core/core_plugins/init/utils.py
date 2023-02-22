from nonebot.plugin import get_loaded_plugins

_ignore_plugins = set(
    [
        "nonebot_plugin_imageutils",
        "nonebot_plugin_apscheduler",
        "nonebot_plugin_htmlrender",
    ]
)

_ignore_modules = set(
    [
        "migang.core.core_plugins.help",
        "migang.core.core_plugins.hooks",
        "migang.core.core_plugins.init",
        "migang.core.core_plugins.switch",
        "migang.core.core_plugins.schedule",
        "migang.core.core_plugins.switch_bot",
        "migang.core.core_plugins.permission_control"
    ]
)


def get_plugin_list():
    plugins = get_loaded_plugins()
    return [
        plugin
        for plugin in plugins
        if (plugin.module_name not in _ignore_modules)
        and (plugin.name not in _ignore_plugins)
    ]
