from pathlib import Path
from typing import Any, Dict

from aerich_config_helper.file_operation import load_data, async_load_data


async def async_load_config(path: Path) -> Dict[str, Any]:
    data = await async_load_data(path)
    return _build_config(data)


def load_config(path: Path) -> Dict[str, Any]:
    data = load_data(path)
    return _build_config(data)


def _build_config(data: dict) -> Dict[str, Any]:
    ret = {
        "connections": {},
        "apps": {
            "models": {
                "models": ["aerich_config_helper.model"],
                "default_connection": "default",
            }
        },
    }
    if data.get("db_url"):
        ret["connections"]["default"] = data["db_url"]
    elif "db_type" not in data or str(data["db_type"]).lower() == "sqlite":
        db_path = Path() / "data" / "db" / "migangbot.db"
        db_path.parent.mkdir(exist_ok=True, parents=True)
        ret["connections"]["default"] = f"sqlite://{db_path}"
    elif (
        "host" in data
        and "port" in data
        and "user" in data
        and "password" in data
        and "database" in data
    ):
        engine: str
        if str(data["db_type"]).lower() == "mysql":
            engine = "mysql"
        elif str(data["db_type"]).lower() == "postgresql":
            engine = "asyncpg"
        ret["connections"]["default"] = {
            "engine": f"tortoise.backends.{engine}",
            "credentials": {
                "host": data["host"],
                "port": str(data["port"]),
                "user": data["user"],
                "password": str(data["password"]),
                "database": data["database"],
            },
        }
    else:
        raise Exception("数据库配置文件未正确填写，请填写db_config.yaml")
    return ret
