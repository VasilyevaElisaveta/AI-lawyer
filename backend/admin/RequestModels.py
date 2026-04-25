from pydantic import BaseModel, Field, model_validator
from string import punctuation, ascii_uppercase, digits
from enum import StrEnum
from datetime import datetime

from db.DatabaseModels import MAX_MESSAGE_RATING, MIN_MESSAGE_RATING, AgentType


class Order(StrEnum):
    ASC = "asc"
    DESC = "desc"


class MessageOrderBy(StrEnum):

    USER_ID = "user_id"
    PROCESSING_TIME = "processing_time"
    RATING = "rating"
    TOKENS = "tokens"
    DATE = "date"
    

class UserOrderBy(StrEnum):

    ID = "id"
    CHATS = "chats"
    TOKENS = "tokens"


class MessageFiltersModel(BaseModel):

    user_id: int | None = None
    agent: list[AgentType] | None = None
    rating: list[int] | None = None
    date_before: datetime | None = None
    date_after: datetime | None = None
    order_by: MessageOrderBy = MessageOrderBy.USER_ID
    order: Order = Order.ASC
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1)

    @model_validator(mode="after")
    def validate_rating(self):

        if self.rating is None:
            return self
        
        for elem in self.rating:
            if not(MIN_MESSAGE_RATING <= elem <= MAX_MESSAGE_RATING):
                raise ValueError(f"Rating must be in [{MIN_MESSAGE_RATING}; {MAX_MESSAGE_RATING}]")
            
        return self


class MessageObject(BaseModel):

    user_id: int
    user_message: str
    ai_message: str
    agent: str
    processing_time: int
    rating: int | None
    tokens: int
    sending_time: datetime


class MessagesModel(BaseModel):

    messages: list[MessageObject]


class MessageRatingObject(BaseModel):

    rating: int
    amount: int


class MessagesRatingsModel(BaseModel):

    statistics: list[MessageRatingObject]


class AppealTypeObject(BaseModel):

    appeal: str
    amount: int


class AppealTypesModel(BaseModel):

    statistics: list[AppealTypeObject]


class AgentTypeObject(BaseModel):

    agent: str
    amount: int


class AgentsTypesModel(BaseModel):

    statistics: list[AgentTypeObject]


class AgentRatingObject(BaseModel):

    agent: str
    rating: float


class AgentsRatingsModel(BaseModel):

    statistics: list[AgentRatingObject]


class UserFiltersModel(BaseModel):

    id: int | None = None
    username: str | None = None
    email: str | None = None
    is_admin: bool | None = None
    name: str | None = None
    surname: str | None = None
    patronymic: str | None = None
    order_by: UserOrderBy = UserOrderBy.ID
    order: Order = Order.ASC
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1)


class UserObject(BaseModel):

    id: int
    username: str
    email: str
    is_admin: bool
    name: str
    surname: str
    patronymic: str | None
    chats: int
    tokens: int


class UsersModel(BaseModel):

    users: list[UserObject]


class ChangePasswordModel(BaseModel):

    new_password: str = Field(min_length=8)

    @model_validator(mode="after")
    def validate_password(self):
        has_digits = False
        has_upper_letters = False
        has_special_characters = False

        unique_letters = set(self.new_password)

        for letter in unique_letters:
            if letter in digits:
                has_digits = True
            elif letter in ascii_uppercase:
                has_upper_letters = True
            elif letter in punctuation:
                has_special_characters = True
        
        if not all([has_digits, has_upper_letters, has_special_characters]):
            raise ValueError("Password must contain digits, special symbols, upper letters and be at least 8 characters long")
        
        return self
