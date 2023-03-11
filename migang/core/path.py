from pathlib import Path

DATA_PATH = (Path() / "data").resolve()
"""数据文件路径，插件的数据建议放这或者插件自己的文件夹
"""
RESOURCE_PATH = (Path() / "resources").resolve()
"""资源文件路径，存放共享资源与非插件资源
"""
IMAGE_PATH = RESOURCE_PATH / "image"
"""资源图片路径，存放共享图片与非插件图片
"""
FONT_PATH = RESOURCE_PATH / "font"
"""资源字体数据，存放共享字体
"""
TEXT_PATH = RESOURCE_PATH / "text"
"""资源文本数据，存放共享文本与非插件文本
"""
TEMPLATE_PATH = RESOURCE_PATH / "template"
"""资源网页模板数据，存放共享网页模板
"""

IMAGE_PATH.mkdir(exist_ok=True, parents=True)
FONT_PATH.mkdir(exist_ok=True, parents=True)
TEXT_PATH.mkdir(exist_ok=True, parents=True)
DATA_PATH.mkdir(exist_ok=True, parents=True)
RESOURCE_PATH.mkdir(exist_ok=True, parents=True)
TEMPLATE_PATH.mkdir(exist_ok=True, parents=True)
