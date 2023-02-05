from pathlib import Path

from tortoise import Tortoise
from tortoise import Tortoise
from tortoise.connection import connections
from migangbot.core.utils.file_operation import async_load_data

from migangbot.core.models import *
from migangbot.models import *


async def _load_config(path: Path):
    data = await async_load_data(path)
    ret = {
        "connections": {},
        "apps": {
            "migangbot": {
                "models": ["migangbot.core.database"],
                # If no default_connection specified, defaults to 'default'
                "default_connection": "default",
            }
        },
        "use_tz": False,
        "timezone": "UTC",
    }
    if data.get("db_url"):
        ret["connections"]["default"] = data["db_url"]
    elif "db_type" not in data or str(data["db_type"]).lower() == "sqlite":
        db_path = Path() / "data" / "sqlite" / "database.db"
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


async def init_db():
    try:
        await Tortoise.init(config=await _load_config(Path() / "db_config.yaml"))
    except Exception as e:
        raise Exception(f"数据库连接失败：{e}")
    await Tortoise.generate_schemas(safe=True)


async def close_db():
    await connections.close_all(discard=True)
