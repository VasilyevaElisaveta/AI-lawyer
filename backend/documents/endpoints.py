from typing import Annotated
from fastapi import APIRouter, Form, Body, Depends, status, HTTPException

from db.Database import Database

from dependencies.dependencies import get_current_user, get_password_hash, get_database



documents_router = APIRouter(prefix="/documents", tags=["documnts"])


@documents_router.get("/")
async def get_documents():
    pass


@documents_router.get("/{document_id}/")
async def get_document(document_id: int):
    pass


@documents_router.delete("/{document_id}/")
async def delete_document(document_id: int):
    pass
