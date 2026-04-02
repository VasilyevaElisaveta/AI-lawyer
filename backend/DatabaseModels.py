from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Column, DateTime, ForeignKey
from datetime import datetime, timezone


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


class Chats(Base):

    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str]
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))


class ChatSummaries(Base):
    
    __tablename__ = "chat_sumaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    summary: Mapped[str]


class UserMessages(Base):

    __tablename__ = "user_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    text: Mapped[str]
    attachment_1: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    attachment_2: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    attachment_3: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))


class ModelMessages(Base):

    __tablename__ = "model_messages"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    text: Mapped[str]
    rating: Mapped[int] = mapped_column(nullable=True)
    attachment_1: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    attachment_2: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    attachment_3: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc))


class Files(Base):

    __tablename__ = "files"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="SET NULL"), nullable=True)
    path: Mapped[str]
