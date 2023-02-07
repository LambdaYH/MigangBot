from pathlib import Path
from typing import Dict, Any

from tortoise import Tortoise
from tortoise.connection import connections

from migang.core.utils.file_operation import async_load_data

from migang.core.models import *
from migang.models import *


async def _load_config(path: Path) -> Dict[str, Any]:
    """从配置文件加载数据库配置

    Args:
        path (Path): 数据库配置文件

    Raises:
        Exception: 若文件不正确，则...

    Returns:
        Dict[str, Any]: config
    """
    data = await async_load_data(path)
    ret = {
        "connections": {},
        "apps": {
            "migangbot": {
                "models": ["migang.core.database"],
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


async def init_db() -> None:
    """初始化数据库，创建不存在的表

    Raises:
        Exception: 若创建失败
    """
    try:
        await Tortoise.init(config=await _load_config(Path() / "db_config.yaml"))
    except Exception as e:
        raise Exception(f"数据库连接失败：{e}")
    await Tortoise.generate_schemas(safe=True)


async def close_db() -> None:
    """程序结束时关闭数据库连接"""
    await connections.close_all(discard=True)
