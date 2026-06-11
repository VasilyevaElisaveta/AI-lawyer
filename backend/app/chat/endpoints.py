import httpx
import json
from typing import Annotated
from fastapi import APIRouter, Query, Body, Form, status, HTTPException
from fastapi.responses import StreamingResponse
from uuid import UUID
from pathlib import Path

from chat.queries import Queries
from chat.RequestModels import (CreateChatResponseModel, ChatsHistoryResponseModel,
                                AllMessagesResponseModel, RatingModel, 
                                OneMessageRequestModel, OneMessageResponseModel,
                                RenameChatModel)
from dependencies.dependencies import CurrentUser, AppDatabase
from db.DatabaseModels import MIN_MESSAGE_RATING, MAX_MESSAGE_RATING

from logger import logger


INFERENCE_URL = "http://inference-server:8000"
chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("/create/",
                  description="Create a new chat.",
                  response_model=CreateChatResponseModel,
                  status_code=status.HTTP_201_CREATED)
async def create_chat(user: CurrentUser, db: AppDatabase):
    
    new_chat = await db.exec_query(Queries.create_chat_query(user.id))

    logger.info(f"User created chat. user_id={user.id} chat_id={new_chat.id}")
    return new_chat


@chat_router.get("/history/",
                 description="Get chats history",
                 response_model=ChatsHistoryResponseModel,
                 status_code=status.HTTP_200_OK)
async def get_history(user: CurrentUser, db: AppDatabase):
    chats = await db.exec_query(Queries.get_chats_history_query(user.id), returning=True, one_or_none=False)

    logger.info(f"User got chat history. user_id={user.id}")
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

    logger.info(f"User got messages from chat. user_id={user.id} chat_id={chat_id}")
    return {"messages": list(messages.values())}


@chat_router.put("/{chat_id}/rename/",
                 description="",
                 response_model=RenameChatModel,
                 status_code=status.HTTP_200_OK)
async def rename_chat(chat_id: UUID, data: Annotated[RenameChatModel, Form()], user: CurrentUser, db: AppDatabase):
    current_chat = await db.exec_query(Queries.get_current_chat_query(chat_id))
    if current_chat is None or user.id != current_chat.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    
    logger.info(f"User rename chat. user_id={user.id} chat_id={chat_id}")
    return await db.exec_query(Queries.rename_chat_query(chat_id, data.new_name))


@chat_router.post("/{chat_id}/message/",
                  description="Send message.",
                  response_model=OneMessageResponseModel,
                  status_code=status.HTTP_200_OK)
async def send_message(chat_id: UUID, data: Annotated[OneMessageRequestModel, Form()], user: CurrentUser, db: AppDatabase):
    current_chat = await db.exec_query(Queries.get_current_chat_query(chat_id))
    if current_chat is None or user.id != current_chat.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    
    if data.agent_type is not None and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the administrator can manually select the agent type")
    
    human_message = await db.exec_query(Queries.add_message_to_chat_query(chat_id, data.message, "human"))

    inference_server_url = f"{INFERENCE_URL}/api/chat/invoke" + (f"/{data.agent_type}" if data.agent_type is not None else "")
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(
            inference_server_url,
            json={
                "raw_input": data.message,
                "thread_id": str(chat_id),
                "user_metadata": {"user_id": str(user.id)}
            }
        )
        response.raise_for_status()
        model_response = response.json()

    if model_response["is_error"]:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=model_response["reply"])

    if current_chat.name is None:
        async with httpx.AsyncClient(timeout=30) as client:
            name_response = await client.post(
                f"{INFERENCE_URL}/api/chat/chat_name",
                json={"raw_input": data.message, "thread_id": str(chat_id)}
            )
            chat_name = name_response.json().get("chat_name", f"Чат {chat_id}")
        await db.exec_query(
            Queries.add_chat_name_and_appeal_type_query(
                chat_id,
                chat_name,
                model_response["process_name"]
            ),
            returning=False
        )

    reply_text = model_response["document_comment"] if model_response["document_created"] else model_response["reply"]

    ai_message = await db.exec_query(
        Queries.add_message_to_chat_query(
            chat_id,
            reply_text,
            "ai",
            model_response["process_name"],
            model_response["total_tokens"],
            model_response["latency_ms"]
        )
    )
    await db.exec_query(Queries.add_message_reply_query(human_message.id, ai_message.id), returning=False)

    ai_message = dict(ai_message)

    if model_response["document_created"]:
        document_path = model_response["reply"]
        print(document_path)
        file = await db.exec_query(
            Queries.create_file_query(Path(document_path).name, user.id, chat_id, document_path)
        )
        await db.exec_query(Queries.add_attachment_query(ai_message["id"], file.id), returning=False)
        ai_message["files"] = await db.exec_query(Queries.get_files_query(ai_message["id"]), one_or_none=False)
    else:
        ai_message["files"] = []

    logger.info(f"User sent message. user_id={user.id} chat_id={chat_id} agent={model_response['process_name']}")
    return {"message": ai_message}


@chat_router.post("/{chat_id}/message/stream/",
                  description="Send message with streaming response.",
                  status_code=status.HTTP_200_OK)
async def send_message_stream(chat_id: UUID, data: Annotated[OneMessageRequestModel, Form()], user: CurrentUser, db: AppDatabase):
    current_chat = await db.exec_query(Queries.get_current_chat_query(chat_id))
    if current_chat is None or user.id != current_chat.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")

    if data.agent_type is not None and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the administrator can manually select the agent type")

    human_message = await db.exec_query(Queries.add_message_to_chat_query(chat_id, data.message, "human"))

    inference_server_url = f"{INFERENCE_URL}/api/chat/invoke" + (f"/{data.agent_type}" if data.agent_type is not None else "") + "/stream"
    async def stream_generator():
        full_reply = ""
        document_comment = ""
        result_event = None

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    inference_server_url,
                    json={
                        "raw_input": data.message,
                        "thread_id": str(chat_id),
                        "user_metadata": {"user_id": str(user.id)}
                    }
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        event = json.loads(line)

                        if event["type"] == "progress":
                            if event["stage"] == "answer":
                                full_reply += event["content"]
                            elif event["stage"] == "document_comment":
                                document_comment += event["content"]
                            yield json.dumps(event, ensure_ascii=False) + "\n"

                        elif event["type"] == "result":
                            result_event = event

                        elif event["type"] == "error":
                            yield json.dumps(event, ensure_ascii=False) + "\n"
                            return

        except httpx.ConnectError:
            yield json.dumps({"type": "error", "message": "Inference server unavailable."}, ensure_ascii=False) + "\n"
            return
        except httpx.TimeoutException:
            yield json.dumps({"type": "error", "message": "Inference server timeout."}, ensure_ascii=False) + "\n"
            return

        if result_event is None:
            yield json.dumps({"type": "error", "message": "No result received."}, ensure_ascii=False) + "\n"
            return

        if result_event["document_created"]:
            reply_text = document_comment
        else:
            reply_text = full_reply if full_reply.strip() else result_event.get("reply", "")

        ai_message = await db.exec_query(
            Queries.add_message_to_chat_query(
                chat_id,
                reply_text,
                "ai",
                result_event["process_name"],
                result_event["total_tokens"],
                result_event["latency_ms"]
            )
        )
        await db.exec_query(Queries.add_message_reply_query(human_message.id, ai_message.id), returning=False)
        ai_message = dict(ai_message)

        if result_event["document_created"]:
            document_path = result_event["reply"]
            file = await db.exec_query(
                Queries.create_file_query(Path(document_path).name, user.id, chat_id, str(document_path))
            )
            await db.exec_query(Queries.add_attachment_query(ai_message["id"], file.id), returning=False)
            ai_message["files"] = await db.exec_query(Queries.get_files_query(ai_message["id"]), one_or_none=False)
        else:
            ai_message["files"] = []

        ai_message["files"] = [dict(f) for f in ai_message["files"]]

        yield json.dumps({
            "message": ai_message
        }, ensure_ascii=False, default=str) + "\n"

        if current_chat.name is None:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    name_response = await client.post(
                        f"{INFERENCE_URL}/api/chat/chat_name",
                        json={"raw_input": data.message, "thread_id": str(chat_id)}
                    )
                    chat_name = name_response.json().get("chat_name", f"Чат {chat_id}")
                await db.exec_query(
                    Queries.add_chat_name_and_appeal_type_query(chat_id, chat_name, result_event["process_name"]),
                    returning=False
                )
            except Exception as e:
                logger.warning(f"Failed to generate chat name: {e}")

        logger.info(f"Stream completed. user_id={user.id} chat_id={chat_id} agent={result_event['process_name']}")

    return StreamingResponse(
        stream_generator(),
        media_type="application/x-ndjson",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache"
        }
    )
    

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

    logger.info(f"User rated message. user_id={user.id} chat_id={chat_id} message_id={message_id}")
    return await db.exec_query(Queries.add_rating_to_message_query(message_id, data.rating))


@chat_router.delete("/{chat_id}/",
                    description="Delete chat.",
                    status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: UUID, user: CurrentUser, db: AppDatabase):
    current_chat = await db.exec_query(Queries.get_current_chat_query(chat_id))
    if current_chat is None or user.id != current_chat.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    
    logger.info(f"User deleted chat. user_id={user.id} chat_id={chat_id}")
    await db.exec_query(Queries.delete_chat_query(chat_id), returning=False)
