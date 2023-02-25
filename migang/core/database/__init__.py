from pathlib import Path
import asyncio
from typing import Any, Dict, Callable

from tortoise import Tortoise
from nonebot import get_driver
from nonebot.log import logger
from nonebot.utils import is_coroutine_callable, run_sync
from tortoise.connection import connections

from migang.core.models import *
from migang.core.utils.file_operation import async_load_data

_post_init_db_func = []
_pre_close_db_func = []


def post_init_db(func: Callable):
    _post_init_db_func.append(func)


def pre_close_db(func: Callable):
    _pre_close_db_func.append(func)


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


async def init_db() -> None:
    """初始化数据库，创建不存在的表

    Raises:
        Exception: 若创建失败
    """
    config = await _load_config(Path() / "db_config.yaml")
    try:
        await Tortoise.init(config=config)
    except Exception as e:
        raise Exception(f"数据库连接失败：{e}")
    await Tortoise.generate_schemas(safe=True)
    # 设定datastore数据库，顺便把datastore的文件都弄到data路径方便找
    env_dict = get_driver().config.dict()
    if (
        "datastore_database_url" in env_dict
        and "datastore_cache_dir" in env_dict
        and "datastore_config_dir" in env_dict
        and "datastore_data_dir" in env_dict
    ):
        pass
    else:
        import re

        import anyio
        from dotenv import dotenv_values

        db_url: str
        if isinstance(config["connections"]["default"], str):
            db_str = config["connections"]["default"]
            db_type = db_str.split(":")[0]
            if db_type == "sqlite":
                db_url = f"sqlite+aiosqlite:/{db_str.split(':')[1]}"
            else:
                db = re.match(r"(\S+)://(\S+:\S+@\S+:\d+/\S+)", db_str)
                db_type = db.group(1)
                if db_type == "mysql":
                    db_url = f"mysql+asyncmy://{db.group(2)}"
                elif db_type == "postgres":
                    db_url = f"postgresql+asyncpg://{db.group(2)}"
        elif isinstance(config["connections"]["default"], dict):
            db_dict = config["connections"]["default"]
            engine = str(db_dict["engine"]).split(".")[-1]
            if engine == "mysql":
                db_url = "mysql+asyncmy"
            elif engine == "asyncpg":
                db_url = "postgresql+asyncpg"
            db_dict = db_dict["credentials"]
            db_url = f"{db_url}://{db_dict['user']}:{db_dict['password']}@{db_dict['host']}:{db_dict['port']}/{db_dict['database']}"

        env_file = Path() / f".env.{get_driver().env}"
        env_values = dotenv_values(env_file)

        env_values["datastore_database_url"] = db_url
        env_values["datastore_cache_dir"] = "data/datastore/cache"
        env_values["datastore_config_dir"] = "data/datastore/config"
        env_values["datastore_data_dir"] = "data/datastore/data"
        async with await anyio.open_file(env_file, "w") as f:
            await f.write("\n".join(f"{k} = {v}" for k, v in env_values.items()))
        raise Exception("数据库配置初次写入.env，请重启")
    cors = [
        func() if is_coroutine_callable(func) else run_sync(func)()
        for func in _post_init_db_func
    ]
    if cors:
        try:
            await asyncio.gather(*cors)
        except Exception:
            logger.error("数据库初始化后执行的函数出错")
            raise


async def close_db() -> None:
    """程序结束时关闭数据库连接"""
    cors = [
        func() if is_coroutine_callable(func) else run_sync(func)()
        for func in _pre_close_db_func
    ]
    if cors:
        try:
            await asyncio.gather(*cors)
        except Exception:
            logger.error("数据库关闭前执行的函数出错")
    await connections.close_all(discard=True)
