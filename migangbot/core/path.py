from pathlib import Path

DATA_PATH = Path() / "data"
RESOURCE_PATH = Path() / "resources"
IMAGE_PATH = RESOURCE_PATH / "image"
FONT_PATH = RESOURCE_PATH / "font"
TEMPLATE_PATH = RESOURCE_PATH / "template"

IMAGE_PATH.mkdir(exist_ok=True, parents=True)
FONT_PATH.mkdir(exist_ok=True, parents=True)
DATA_PATH.mkdir(exist_ok=True, parents=True)
RESOURCE_PATH.mkdir(exist_ok=True, parents=True)
TEMPLATE_PATH.mkdir(exist_ok=True, parents=True)
