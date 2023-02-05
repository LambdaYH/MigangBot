from pathlib import Path

from tortoise import Tortoise, run_async

from migangbot.core.utils.file_operation import async_load_data


async def _load_config(path: Path):
    data = await async_load_data(path)
    ret = {
        "connections": {
            # Dict format for connection
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": "localhost",
                    "port": "5432",
                    "user": "tortoise",
                    "password": "qwerty123",
                    "database": "test",
                },
            },
            # Using a DB_URL string
            "default": "postgres://postgres:qwerty123@localhost:5432/test",
        },
        "apps": {
            "my_app": {
                "models": ["__main__"],
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
        db_path = Path() / "data" / "database.db"
        db_path.mkdir(exist_ok=True, parents=True)
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
            engine = "asyncmy"
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
    return ret


async def init_db():
    await Tortoise.init(config=await _load_config(Path() / "db_config.yaml"))
    await Tortoise.generate_schemas()
