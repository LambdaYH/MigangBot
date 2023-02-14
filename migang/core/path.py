from pathlib import Path

DATA_PATH = Path() / "data"
"""数据文件路径
"""
RESOURCE_PATH = Path() / "resources"
"""资源文件路径
"""
IMAGE_PATH = RESOURCE_PATH / "image"
"""资源图片路径
"""
FONT_PATH = RESOURCE_PATH / "font"
"""资源字体数据
"""
TEXT_PATH = RESOURCE_PATH / "text"
"""资源文本数据
"""
TEMPLATE_PATH = RESOURCE_PATH / "template"
"""资源网页模板数据
"""

IMAGE_PATH.mkdir(exist_ok=True, parents=True)
FONT_PATH.mkdir(exist_ok=True, parents=True)
TEXT_PATH.mkdir(exist_ok=True, parents=True)
DATA_PATH.mkdir(exist_ok=True, parents=True)
RESOURCE_PATH.mkdir(exist_ok=True, parents=True)
TEMPLATE_PATH.mkdir(exist_ok=True, parents=True)
