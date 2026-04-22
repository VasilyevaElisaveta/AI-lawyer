from sqlalchemy import select, insert, update, delete

from db.DatabaseModels import User


class Queries:

    @staticmethod
    def create_user_query(username: str, email: str, hashed_password: str, name: str, surname: str, patronymic: str | None=None, is_admin: bool=False):
        query = (
            insert(User)
            .values(username=username, email=email, password=hashed_password, name=name, surname=surname, patronymic=patronymic, is_admin=is_admin)
            .returning(User.name, User.surname, User.patronymic, User.username, User.email)
        )
        return query

    @staticmethod
    def get_user_query(value: str, by_username: bool=True):
        query = select(User.id, User.name, User.surname, User.patronymic, User.username, User.email, User.password).select_from(User)
        if by_username:
            query = query.filter_by(username=value)
        else:
            query = query.filter_by(email=value)
        return query
    
    @staticmethod
    def update_user_query(user_id: int, new_user_data: dict):
        query = (update(User)
                 .filter_by(id=user_id)
                 .values(**new_user_data)
                 .returning(User.name, User.surname, User.patronymic, User.username, User.email))
        return query
    
    @staticmethod
    def change_password_query(user_id: int, new_hashed_password: str):
        query = update(User).filter_by(id=user_id).values(password=new_hashed_password)
        return query
    
    @staticmethod
    def delete_user_query(user_id: int):
        query = delete(User).filter_by(id=user_id)
        return query