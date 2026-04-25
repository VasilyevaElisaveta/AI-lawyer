from pydantic import BaseModel
from datetime import datetime


class DocumentObject(BaseModel):

    id: int
    file_name: str
    chat_name: str | None
    created_at: datetime


class DocumentsResponseModel(BaseModel):

    documents: list[DocumentObject]
