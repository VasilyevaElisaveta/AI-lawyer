from os import getenv
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlite3 import Connection

from db.DatabaseModels import Base


class Database:
    __SYNC_PATH_BASE = "sqlite:///"
    __ASYNC_PATH_BASE = "postgresql+asyncpg://"

    def __init__(self, is_sync: bool=True, is_temp: bool=False, detail: bool=False):
        self.__is_sync = is_sync
        self.__is_temp = is_temp
        if self.__is_sync:
            if is_temp:
                self.__temp_db_dir = TemporaryDirectory()
                url = Database.__SYNC_PATH_BASE + self.__temp_db_dir.name + "/temp.db"
            else:
                url = Database.__SYNC_PATH_BASE + "database.db"
            
            self.__engine = create_engine(
                url,
                echo=detail
            )

            @event.listens_for(self.__engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                if isinstance(dbapi_connection, Connection):
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.close()
            
            self.__session = sessionmaker(self.__engine)
        else:
            user = getenv("POSTGRES_USER", "<Postgres user>")
            password = getenv("POSTGRES_PASSWORD", "<Postgres user password>")
            host = getenv("POSTGRES_HOST", "<Postgres host>")
            port = getenv("POSTGRES_PORT", "<Postgres port>")
            db = getenv("POSTGRES_DB", "<Postgres db>")
            self.__engine = create_async_engine(
                Database.__ASYNC_PATH_BASE + f"{user}:{password}@{host}:{port}/{db}",
                echo=detail
            )
            self.__session = async_sessionmaker(self.__engine)

    async def reset(self):
        if self.__is_sync:
            Base.metadata.drop_all(self.__engine)
            Base.metadata.create_all(self.__engine)
        else:
            async with self.__engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)

    def close(self):
        self.__engine.dispose()

        if self.__is_sync and self.__is_temp:
            self.__temp_db_dir.cleanup()

    def __exec_sync(self, query, returning: bool):
        with self.__session() as session:
            result = session.execute(query)
            if returning:
                result = result.mappings().all()
            session.commit()
            return result

    async def __exec_async(self, query, returning: bool):
        async with self.__session() as session:
            result = await session.execute(query)
            if returning:
                result = result.mappings().all()
            await session.commit()
            return result
        
    async def exec_query(self, query, returning: bool=True, one_or_none: bool=True):
        if self.__is_sync:
            result = self.__exec_sync(query, returning)
        else:
            result = await self.__exec_async(query, returning)
        
        if not returning:
            return
        
        if one_or_none:
            return result[0] if len(result) != 0 else None
        else:
            return result
