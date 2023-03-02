"""
Database Class
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncContextManager

import sqlalchemy as sqla
from databases import Database

from acsps.env import ACSPS_SQLITE_PATH
from acsps.database.tables import table_metadata


class _Database:
    url = f"sqlite+aiosqlite:///{ACSPS_SQLITE_PATH}"
    rollback = False

    def __init__(self):
        if os.environ.get("PYTEST_ENV", None):
            self.url = f"{self.url}.test"

        # disable databases' logger
        logging.getLogger("databases").propagate = False

        self.db = Database(self.url, force_rollback=self.rollback)
        logging.info(f"Database URI: {self.url.__repr__()}")

    def create_tables(self):
        url = self.url.replace("sqlite+aiosqlite", "sqlite")
        engine = sqla.create_engine(url)
        table_metadata.create_all(engine)

    @asynccontextmanager
    async def acquire(self) -> AsyncContextManager[Database]:
        await self.db.connect()
        try:
            yield self.db
        finally:
            await self.db.disconnect()


database = _Database()


def create_database_tables():
    database.create_tables()
