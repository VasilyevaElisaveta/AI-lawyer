from pydantic import BaseModel


class DocumentObject(BaseModel):

    id: int
    file_name: str
    chat_name: str | None


class DocumentsResponse(BaseModel):

    documents: list[DocumentObject]
