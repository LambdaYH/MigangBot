from pathlib import Path

from aerich_config_helper.config_loader import load_config

TORTOISE_ORM = load_config(Path() / "db_config.yaml")
