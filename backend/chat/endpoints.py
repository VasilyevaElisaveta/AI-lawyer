from typing import Annotated
from fastapi import APIRouter, Query, Body, Form, status, HTTPException
from uuid import UUID, uuid4
from docx import Document
from pathlib import Path
from dotenv import load_dotenv
from os import getenv

from chat.queries import Queries
from chat.RequestModels import (CreateChatResponseModel, ChatsHistoryResponseModel,
                                AllMessagesResponseModel, RatingModel, 
                                OneMessageRequestModel, OneMessageResponseModel)
from dependencies.dependencies import CurrentUser, AppDatabase
from db.DatabaseModels import MIN_MESSAGE_RATING, MAX_MESSAGE_RATING


load_dotenv()


chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("/create/",
                  description="Create a new chat.",
                  response_model=CreateChatResponseModel,
                  status_code=status.HTTP_201_CREATED)
async def create_chat(user: CurrentUser, db: AppDatabase):
    return await db.exec_query(Queries.create_chat_query(user.id))


@chat_router.get("/history/",
                 description="Get chats history",
                 response_model=ChatsHistoryResponseModel,
                 status_code=status.HTTP_200_OK)
async def get_history(user: CurrentUser, db: AppDatabase):
    chats = await db.exec_query(Queries.get_chats_history_query(user.id), returning=True, one_or_none=False)
    return {"chats": chats}
    

@chat_router.get("/{chat_id}/",
                 description="Get chat messages",
                 response_model=AllMessagesResponseModel,
                 status_code=status.HTTP_200_OK)
async def get_chat_messages(chat_id: UUID, user: CurrentUser, db: AppDatabase,
                            limit: Annotated[int, Query(ge=1, le=50)]=20,
                            before_id: Annotated[int | None, Query(ge=1)]=None):
    current_chat = await db.exec_query(Queries.get_current_chat_query(chat_id))
    if current_chat is None or user.id != current_chat.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    
    before_time = None
    if before_id is not None:
        row = await db.exec_query(Queries.get_message_sending_time_query(before_id))
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        before_time = row.sent_at

    rows = await db.exec_query(Queries.get_chat_messages_query(chat_id, limit, before_time), one_or_none=False)

    messages = {}
    for row in rows:
        if row.id not in messages:
            messages[row.id] = {
                "id": row.id,
                "text": row.text,
                "role": row.role,
                "rating": row.rating,
                "files": [],
            }
        if row.file_id is not None:
            messages[row.id]["files"].append({"id": row.file_id, "name": row.file_name})

    return {"messages": list(messages.values())}


@chat_router.post("/{chat_id}/message/",
                  description="Send message.",
                  response_model=OneMessageResponseModel,
                  status_code=status.HTTP_200_OK)
async def send_message(chat_id: UUID, data: Annotated[OneMessageRequestModel, Form()], user: CurrentUser, db: AppDatabase):
    current_chat = await db.exec_query(Queries.get_current_chat_query(chat_id))
    if current_chat is None or user.id != current_chat.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    
    if current_chat.name is None:
        from datetime import datetime

        name = f"chat {datetime.now()}"
        appeal_type = f"appeal {datetime.now().time()}"
        await db.exec_query(Queries.add_chat_name_and_appeal_type_query(chat_id, name, appeal_type), returning=False)
    
    human_message = await db.exec_query(Queries.add_message_to_chat_query(chat_id, data.message, "human"))

    # AI template
    from random import randint, choice
    tokens = randint(100, 500)
    processing_time = randint(0, 100)
    agent = choice(["contract", "lawsuit", "pretrial_claim", "general_question"])
    model_answer = f"Пользователь написал: {data.message}"
    ai_message = await db.exec_query(Queries.add_message_to_chat_query(chat_id, model_answer, "ai", agent, tokens, processing_time))
    await db.exec_query(Queries.add_message_reply_query(human_message.id, ai_message.id), returning=False)

    ai_message = dict(ai_message)
    if data.message == "Напиши документ":
        storage_dir = Path(getenv("storage_path", "storage"))
        storage_dir.mkdir(exist_ok=True)
        
        user_storage_dir = storage_dir / Path(user.username)
        user_storage_dir.mkdir(exist_ok=True)
        
        document_user_name = data.message
        document_system_name = f"{uuid4()}.docx"
        document_path = str(user_storage_dir / document_system_name)
        document = Document()
        document.add_paragraph(model_answer)
        document.save(document_path)

        file = await db.exec_query(Queries.create_file_query(document_user_name, user.id, chat_id, document_path))
        await db.exec_query(Queries.add_attachment_query(ai_message["id"], file.id), returning=False)

        ai_message["files"] = await db.exec_query(Queries.get_files_query(ai_message["id"]), one_or_none=False)
    else:
        ai_message["files"] = []

    return {"message": ai_message}
    

@chat_router.post("/{chat_id}/message/{message_id}/rate/",
                  description=f"Rate message from {MIN_MESSAGE_RATING} to {MAX_MESSAGE_RATING}.",
                  response_model=RatingModel,
                  status_code=status.HTTP_200_OK)
async def rate_message(chat_id: UUID, message_id: int, data: Annotated[RatingModel, Body()], user: CurrentUser, db: AppDatabase):
    current_chat = await db.exec_query(Queries.get_current_chat_query(chat_id))
    if current_chat is None or user.id != current_chat.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")

    current_message = await db.exec_query(Queries.get_message_query(message_id))
    if current_message is None or chat_id != current_message.chat_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
    
    if current_message.role != "ai":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User can rate only ai messages.")

    return await db.exec_query(Queries.add_rating_to_message_query(message_id, data.rating))


@chat_router.delete("/{chat_id}/",
                    description="Delete chat.",
                    status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: UUID, user: CurrentUser, db: AppDatabase):
    current_chat = await db.exec_query(Queries.get_current_chat_query(chat_id))
    if current_chat is None or user.id != current_chat.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    
    await db.exec_query(Queries.delete_chat_query(chat_id), returning=False)
