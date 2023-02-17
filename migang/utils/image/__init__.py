import base64
from io import BytesIO

from PIL import Image


def pic_to_bytes(pic: Image) -> str:
    with BytesIO() as buf:
        pic.save(buf, format="PNG")
        return buf.getvalue()


def pic_to_b64(pic: Image) -> str:
    base64_str = base64.b64encode(pic_to_bytes(pic)).decode()
    return "base64://" + base64_str
