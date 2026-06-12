from sqlalchemy import select, func, distinct
from sqlalchemy.orm import aliased

from admin.RequestModels import UserFiltersModel, MessageFiltersModel, UserOrderBy, MessageOrderBy, Order
from db.DatabaseModels import Chat, Message, User, MessageReply


class Queries:

    @staticmethod
    def get_messages_query(filters: MessageFiltersModel):
        user_msg = aliased(Message)
        ai_msg = aliased(Message)

        tokens = ai_msg.used_tokens.label("tokens")

        query = (
            select(
                Chat.user_id,
                user_msg.text.label("user_message"),
                ai_msg.text.label("ai_message"),
                ai_msg.agent_type.label("agent"),
                ai_msg.processing_time,
                ai_msg.rating,
                tokens,
                user_msg.sent_at.label("sending_time"),
            )
            .select_from(MessageReply)
            .join(user_msg, user_msg.id == MessageReply.message_id)
            .join(ai_msg, ai_msg.id == MessageReply.reply_id)
            .join(Chat, Chat.id == user_msg.chat_id)
        )

        if filters.user_id is not None:
            query = query.filter(Chat.user_id == filters.user_id)
        if filters.agent is not None:
            query = query.filter(ai_msg.agent_type.in_(filters.agent))
        if filters.rating is not None:
            query = query.filter(ai_msg.rating.in_(filters.rating))
        if filters.date_before is not None:
            query = query.filter(user_msg.sent_at <= filters.date_before)
        if filters.date_after is not None:
            query = query.filter(user_msg.sent_at >= filters.date_after)

        order_columns = {
            MessageOrderBy.USER_ID: Chat.user_id,
            MessageOrderBy.PROCESSING_TIME: ai_msg.processing_time,
            MessageOrderBy.RATING: ai_msg.rating,
            MessageOrderBy.TOKENS: tokens,
            MessageOrderBy.DATE: user_msg.sent_at,
        }
        column = order_columns[filters.order_by]
        if filters.order is Order.ASC:
            query = query.order_by(column.asc())
        else:
            query = query.order_by(column.desc())

        query = query.offset((filters.page - 1) * filters.limit).limit(filters.limit)

        return query
    
    @staticmethod
    def get_messages_retings_amount_query():
        query = (
            select(Message.rating, func.count(Message.rating).label("amount"))
            .filter(Message.rating.is_not(None))
            .group_by(Message.rating).order_by(Message.rating)
        )
        return query
    
    @staticmethod
    def get_appeal_types_amount_query():
        query = (
            select(Chat.appeal_type.label("appeal"), func.count(Chat.appeal_type).label("amount"))
            .filter(Chat.appeal_type.is_not(None))
            .group_by(Chat.appeal_type).order_by(Chat.appeal_type)
        )
        return query
    
    @staticmethod
    def get_agents_types_query():
        query = (
            select(Message.agent_type.label("agent"), func.count(Message.agent_type).label("amount"))
            .filter(Message.agent_type.is_not(None))
            .group_by(Message.agent_type).order_by(Message.agent_type)
        )
        return query
    
    @staticmethod
    def get_agents_ratings_query():
        query = (
            select(Message.agent_type.label("agent"), func.round(func.avg(Message.rating), 2).label("rating"))
            .filter(Message.agent_type.is_not(None), Message.rating.is_not(None))
            .group_by(Message.agent_type).order_by(Message.agent_type)
        )
        return query

    @staticmethod
    def get_users_query(filters: UserFiltersModel):

        chats = func.count(distinct(Chat.id)).label("chats")
        tokens = func.sum(func.coalesce(Message.used_tokens, 0)).label("tokens")

        query = (
            select(User.id, User.username, User.email,
                   User.is_admin, User.name, User.surname,
                   User.patronymic, chats, tokens)
            .outerjoin_from(User, Chat, User.id == Chat.user_id)
            .outerjoin(Message, Message.chat_id == Chat.id)
            .group_by(User.id)
        )

        if filters.id is not None:
            query = query.filter(User.id == filters.id)
        if filters.username is not None:
            query = query.filter(User.username.ilike(f"{filters.username}%"))
        if filters.email is not None:
            query = query.filter(User.email.ilike(f"{filters.email}%"))
        if filters.is_admin is not None:
            query = query.filter(User.is_admin == filters.is_admin)
        if filters.name is not None:
            query = query.filter(User.name.ilike(f"{filters.name}%"))
        if filters.surname is not None:
            query = query.filter(User.surname.ilike(f"{filters.surname}%"))
        if filters.patronymic is not None:
            query = query.filter(User.patronymic.ilike(f"{filters.patronymic}%"))

        order_columns = {
            UserOrderBy.ID: User.id,
            UserOrderBy.CHATS: chats,
            UserOrderBy.TOKENS: tokens,
        }
        column = order_columns[filters.order_by]
        if filters.order is Order.ASC:
            query = query.order_by(column.asc())
        else:
            query = query.order_by(column.desc())

        query = query.offset((filters.page - 1)* filters.limit).limit(filters.limit)
        
        return query
