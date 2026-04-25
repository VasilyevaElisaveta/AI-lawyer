from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Column, DateTime, ForeignKey
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID
from enum import StrEnum


MAX_ATTACHMENTS_AMOUNT = 3
MAX_MESSAGE_RATING = 5
MIN_MESSAGE_RATING = 1


class ChatRole(StrEnum):

    USER = "human"
    AI = "ai"


class AgentType(StrEnum):

    CONTRACT = "contract"
    LAWSUIT = "lawsuit" 
    PRETRIAL_CLAIM = "pretrial_claim" 
    GENERAL_QUESTION = "general_question"


class Base(DeclarativeBase):
    pass


class User(Base):

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]
    is_admin: Mapped[bool] = mapped_column(default=False)

    name: Mapped[str]
    surname: Mapped[str]
    patronymic: Mapped[str | None]


class Chat(Base):

    __tablename__ = "chats"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str | None]
    appeal_type: Mapped[str | None]
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))


class ChatSummary(Base):
    
    __tablename__ = "chat_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    summary: Mapped[str]


class Message(Base):

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    text: Mapped[str]
    role: Mapped[ChatRole]
    rating: Mapped[int | None]
    agent_type: Mapped[str | None]
    used_tokens: Mapped[int| None]
    processing_time: Mapped[int | None]
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))


class MessageReply(Base):

    __tablename__ = "message_replies"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    reply_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))


class Attachment(Base):

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"))


class File(Base):

    __tablename__ = "files"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    chat_id: Mapped[UUID | None] = mapped_column(ForeignKey("chats.id", ondelete="SET NULL"))
    path: Mapped[str]
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))
