"""基于https://github.com/lgc2333/nonebot-plugin-picmcstat
"""

import asyncio
from typing import Optional

import aiosqlite


class ServerDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.__connection: aiosqlite.Connection = None
        asyncio.get_event_loop().run_until_complete(self.__create_table())

    async def __create_table(self):
        try:
            conn = await self.__connect()
            await conn.execute(
                """CREATE TABLE IF NOT EXISTS McServerDBGroup
                          (id        INTEGER          ,
                           name      TEXT             ,
                           host      TEXT     NOT NULL,
                           port      INTEGER          ,
                           sv_type   TEXT     NOT NULL);"""
            )
            await conn.execute(
                """CREATE TABLE IF NOT EXISTS McServerDBPrivate
                          (id        INTEGER          ,
                           name      TEXT             ,
                           host      TEXT     NOT NULL,
                           port      INTEGER          ,
                           sv_type   TEXT     NOT NULL);"""
            )
        except Exception as e:
            raise Exception(f"创建表发生错误: {e}")

    async def __connect(self) -> aiosqlite.Connection:
        if not self.__connection:
            self.__connection = await aiosqlite.connect(self.db_path)
        return self.__connection

    async def add_server(
        self,
        group_id: int,
        user_id: int,
        name: str,
        host: str,
        port: Optional[int],
        sv_type: str,
    ):
        """
        添加服务器
        """
        conn = await self.__connect()
        await conn.execute(
            f"INSERT INTO McServerDB{'Group' if group_id else 'Private'} (id, name, host, port, sv_type) \
                            VALUES (?,?,?,?,?)",
            (group_id if group_id else user_id, name, host, port, sv_type),
        )
        await conn.commit()

    async def del_server(
        self, group_id: Optional[int], user_id: Optional[int], name: str
    ):
        """
        删除服务器
        """
        conn = await self.__connect()
        await conn.execute(
            f"DELETE FROM McServerDB{'Group' if group_id else 'Private'} WHERE id=? AND name=?",
            (group_id if group_id else user_id, name),
        )
        await conn.commit()

    async def get_server(
        self, group_id: Optional[int], user_id: Optional[int], name: str
    ):
        """
        获取以name命名的服务器
        """
        conn = await self.__connect()
        return await (
            await conn.execute(
                f"SELECT host, port, sv_type FROM McServerDB{'Group' if group_id else 'Private'} WHERE id=? AND name=?",
                (group_id if group_id else user_id, name),
            )
        ).fetchone()

    async def get_server_list(self, group_id: Optional[int], user_id: Optional[int]):
        """
        获取服务器列表
        返回name host port sv_type
        """
        conn = await self.__connect()
        return await (
            await conn.execute(
                f"SELECT name, host, port, sv_type FROM McServerDB{'Group' if group_id else 'Private'} WHERE id=?",
                (group_id if group_id else user_id,),
            )
        ).fetchall()
