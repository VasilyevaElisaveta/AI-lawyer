from os import getenv
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from DatabaseModels import Base, User


class Database:
    __SYNC_PATH_BASE = "sqlite:///"
    __ASYNC_PATH_BASE = "postgresql+asyncpg://"

    def __init__(self, is_sync: bool=True, detail: bool=False):
        self.__is_sync = is_sync
        if self.__is_sync:
            self.__temp_db_dir = TemporaryDirectory()
            self.__engine = create_engine(
                Database.__SYNC_PATH_BASE + self.__temp_db_dir.name + "/temp.db",
                echo=detail
            )
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

        if self.__is_sync:
            self.__temp_db_dir.cleanup()

    def __exec_sync(self, query):
        with self.__session() as session:
            return session.execute(query)

    async def __exec_async(self, query):
        async with self.__session() as session:
            return await session.execute(query)

    async def __exec_query(self, query):
        if self.__is_sync:
            return self.__exec_sync(query)
        return await self.__exec_async(query)
    
    async def create_object(self, object):
        if self.__is_sync:
            self.__create_sync(object)
        else:
            self.__create_async(object)

    def __create_sync(self, object):
        with self.__session() as session:
            session.add(object)
            session.commit()

    async def __create_async(self, object):
        async with self.__session() as session:
            session.add(object)
            await session.commit()
    
    @staticmethod
    def __get_user_query(value: str, by_username: bool):
        query = select(User.id, User.name, User.surname, User.patronymic, User.username, User.email, User.password).select_from(User)
        if by_username:
            query = query.filter_by(username=value)
        else:
            query = query.filter_by(email=value)
        return query
    
    async def get_user(self, value: str, by_username: bool=True):
        query = Database.__get_user_query(value, by_username)
        result = await self.__exec_query(query)
        return result.mappings().one_or_none()
    
    async def create_user(self, username: str, email: str, password: str, name: str, surname: str, patronymic: str | None):
        new_user = User(username=username, email=email, password=password, name=name, surname=surname, patronymic=patronymic)
        await self.create_object(new_user)
