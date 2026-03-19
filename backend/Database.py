from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from DatabaseModels import Base, User


class Database:
    
    def __init__(self):
        self.__engine = create_engine("sqlite:///temp.db")
        self.__session = sessionmaker(self.__engine)

        Base.metadata.drop_all(self.__engine)
        Base.metadata.create_all(self.__engine)

    def create_user(self, username: str, password: str):
        with self.__session() as session:
            user = User(username=username, password=password)
            session.add(user)

            try:
                session.commit()
                return user.id
            except IntegrityError:
                session.rollback()
                return None

    def close(self):
        self.__engine.dispose()
