import aiosqlite


class ImageData:
    def __init__(self, db_path):
        self.db_path = db_path
        self._connection: aiosqlite.Connection = None

    async def _connect(self) -> aiosqlite.Connection:
        if not self._connection:
            self._connection = await aiosqlite.connect(self.db_path)
        return self._connection

    async def get_random_image(self, table: str) -> str:
        async with await (await self._connect()).execute(
            f"SELECT LINK FROM {table.upper()}IMAGELINK ORDER BY RANDOM() LIMIT 1"
        ) as cursor:
            return (await cursor.fetchone())[0]
