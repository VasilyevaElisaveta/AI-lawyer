from sqlalchemy import select, insert, delete, update
from datetime import datetime
from uuid import UUID

from db.DatabaseModels import Chat, Message, Attachment, File


class Queries:

    @staticmethod
    def create_chat_query(user_id: int):
        query = insert(Chat).values(user_id=user_id).returning(Chat.id)
        return query

    @staticmethod
    def get_chats_history(user_id: int):
        query = select(Chat.id, Chat.name, Chat.created_at).filter_by(user_id=user_id).order_by(Chat.created_at.desc())
        return query

    @staticmethod
    def get_current_chat(chat_id: UUID):
        query = select(Chat.id, Chat.user_id, Chat.name, Chat.appeal_type).filter_by(id=chat_id)
        return query
    
    @staticmethod
    def get_message_sending_time(message_id: int):
        query = select(Message.sent_at).filter_by(id=message_id)
        return query

    @staticmethod
    def get_chat_messages(chat_id: UUID, limit: int, before_time: datetime | None):
        query = (
            select(
                Message.id,
                Message.text,
                Message.role,
                Message.sent_at,
                File.id.label("file_id"),
                File.name.label("file_name"),
            )
            .outerjoin(Attachment, Attachment.message_id == Message.id)
            .outerjoin(File, File.id == Attachment.file_id)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.sent_at)
            .limit(limit)
        )
        if before_time is not None:
            query = query.where(Message.sent_at < before_time)

        return query
    
    @staticmethod
    def add_chat_name_and_appeal_type_query(chat_id: UUID, name: str, appeal_type: str):
        query = update(Chat).filter_by(id=chat_id).values(name=name, appeal_type=appeal_type)
        return query

    @staticmethod
    def add_message_to_chat_query(chat_id: UUID, text: str, role: str):
        query = insert(Message).values(chat_id=chat_id, text=text, role=role).returning(Message.text)
        return query

    @staticmethod
    def get_message(message_id: int):
        query = select(Message.id, Message.chat_id, Message.text, Message.role, Message.rating).filter_by(id=message_id)
        return query

    @staticmethod
    def add_rating_to_message_query(message_id: int, rating: int):
        query = update(Message).filter_by(id=message_id).values(rating=rating).returning(Message.rating)
        return query

    @staticmethod
    def delete_chat_query(chat_id: UUID):
        query = delete(Chat).filter_by(id=chat_id)
        return query