from sqlalchemy import select, delete

from db.DatabaseModels import Chat, File


class Queries:

    @staticmethod
    def get_user_documents_query(user_id: int):
        query = (
            select(File.id, File.name.label("file_name"), Chat.name.label("chat_name"), File.created_at)
            .join_from(File, Chat, File.chat_id == Chat.id).filter(File.user_id == user_id)
            .order_by(File.created_at)
        )
        return query
    
    @staticmethod
    def get_document_query(document_id: int):
        query = select(File.id, File.name, File.path, File.user_id).filter_by(id=document_id)
        return query

    @staticmethod
    def delete_document_query(document_id: int):
        query = delete(File).filter_by(id=document_id)
        return query
