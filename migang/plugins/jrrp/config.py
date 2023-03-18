from pydantic import Extra, BaseModel


class Config(BaseModel, extra=Extra.ignore):
    fortune_style: str = "summer"
