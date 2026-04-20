from os import getenv
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from db.DatabaseModels import Base, User


class Database:
    __SYNC_PATH_BASE = "sqlite:///"
    __ASYNC_PATH_BASE = "postgresql+asyncpg://"

    def __init__(self, is_sync: bool=True, detail: bool=False, is_temp: bool=False):
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

    async def __exec_query(self, query, returning: bool=True):
        if self.__is_sync:
            return self.__exec_sync(query, returning)
        return await self.__exec_async(query, returning)
    
    async def create_object(self, object):
        if self.__is_sync:
            return self.__create_sync(object)
        else:
            return self.__create_async(object)

    def __create_sync(self, object):
        with self.__session() as session:
            session.add(object)
            session.commit()
            session.refresh(object)
            return object

    async def __create_async(self, object):
        async with self.__session() as session:
            session.add(object)
            await session.commit()
            await session.refresh(object)
            return object
    
    @staticmethod
    def __get_user_query(value: str, by_username: bool):
        query = select(User.id, User.name, User.surname, User.patronymic, User.username, User.email, User.password).select_from(User)
        if by_username:
            query = query.filter_by(username=value)
        else:
            query = query.filter_by(email=value)
        return query
    
    @staticmethod
    def __get_update_user_query(user_id: int, new_user_data: dict):
        query = (update(User)
                 .filter_by(id=user_id)
                 .values(**new_user_data)
                 .returning(User.name, User.surname, User.patronymic, User.username, User.email))
        return query
    
    @staticmethod
    def __get_change_password_query(user_id: int, new_password: str):
        query = update(User).filter_by(id=user_id).values(password=new_password)
        return query
    
    @staticmethod
    def __get_delete_user_query(user_id: int):
        query = delete(User).filter_by(id=user_id)
        return query
    
    async def create_user(self, username: str, email: str, password: str, name: str, surname: str, patronymic: str | None):
        new_user = User(username=username, email=email, password=password, name=name, surname=surname, patronymic=patronymic)
        return await self.create_object(new_user)
    
    async def get_user(self, value: str, by_username: bool=True):
        query = Database.__get_user_query(value, by_username)
        result = await self.__exec_query(query)
        return result[0] if len(result) != 0 else None
    
    async def update_user_info(self, user_id: int, new_user_data: dict):
        query = Database.__get_update_user_query(user_id, new_user_data)
        updated_user = await self.__exec_query(query)
        return updated_user[0]
    
    async def change_password(self, user_id: int, new_password: str):
        query = Database.__get_change_password_query(user_id, new_password)
        await self.__exec_query(query)

    async def delete_user(self, user_id: int):
        query = Database.__get_delete_user_query(user_id)
        await self.__exec_query(query, returning=False)
