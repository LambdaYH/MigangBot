from io import BytesIO

from .picmcstat.draw import MARGIN, MIN_WIDTH, draw_bg, format_extra


def draw_list(list_text: str) -> BytesIO:
    list_text = format_extra(list_text)
    BG_WIDTH = list_text.width + MARGIN * 2 if list_text else MIN_WIDTH
    BG_HEIGHT = MARGIN * 2 + list_text.height
    if BG_WIDTH < MIN_WIDTH:
        BG_WIDTH = MIN_WIDTH
    bg = draw_bg(BG_WIDTH, BG_HEIGHT)
    list_text.draw_on_image(
        bg.image,
        (MARGIN, MARGIN),
    )

    return bg.convert("RGB").save("PNG")
