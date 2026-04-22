from typing import Annotated
from fastapi import APIRouter, Form, Body, Depends, status, HTTPException

from db.Database import Database

from dependencies.dependencies import get_current_user, get_password_hash, get_database



statistics_router = APIRouter(prefix="/statistics", tags=["statistics"])


@statistics_router.get("/messages/")
async def get_messages_statistics():
    pass


@statistics_router.get("/messages/ratings/")
async def get_messages_ratings_statistics():
    pass


@statistics_router.get("/appeal_types/")
async def get_appeal_types_statistics():
    pass
