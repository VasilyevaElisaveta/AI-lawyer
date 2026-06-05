from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

from db.DatabaseModels import MAX_MESSAGE_RATING, MIN_MESSAGE_RATING


class CreateChatResponseModel(BaseModel):

    id: UUID


class ChatObject(BaseModel):

    id: UUID
    name: str | None
    created_at: datetime


class ChatsHistoryResponseModel(BaseModel):

    chats: list[ChatObject]


class FileObject(BaseModel):

    id: int
    name: str
    

class MessageObject(BaseModel):

    id: int
    text: str
    role: str
    rating: int | None
    files: list[FileObject]


class AllMessagesResponseModel(BaseModel):

    messages: list[MessageObject]


class OneMessageRequestModel(BaseModel):

    message: str


class OneMessageResponseModel(BaseModel):

    message: MessageObject


class RatingModel(BaseModel):

    rating: int = Field(ge=MIN_MESSAGE_RATING, le=MAX_MESSAGE_RATING)


class RenameChatModel(BaseModel):

    new_name: str
