from fastapi import APIRouter, status, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from documents.queries import Queries
from documents.RequestModels import DocumentsResponseModel
from dependencies.dependencies import CurrentUser, AppDatabase


documents_router = APIRouter(prefix="/documents", tags=["documnts"])


@documents_router.get("/",
                      description="Get user files.",
                      response_model=DocumentsResponseModel,
                      status_code=status.HTTP_200_OK)
async def get_documents(user: CurrentUser, db: AppDatabase):
    documents = await db.exec_query(Queries.get_user_documents_query(user.id), one_or_none=False)
    return {"documents": documents}


@documents_router.get("/{document_id}/",
                      description="Download document.",
                      response_class=FileResponse,
                      status_code=status.HTTP_200_OK)
async def get_document(document_id: int, user: CurrentUser, db: AppDatabase):
    document = await db.exec_query(Queries.get_document(document_id))
    if document is None or document.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    
    if not Path(document.path).exists():
        await db.exec_query(Queries.delete_document_query(document_id), returning=False)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    
    return FileResponse(
        path=document.path,
        filename=document.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@documents_router.delete("/{document_id}/",
                         description="Delete document.",
                         status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: int, user: CurrentUser, db: AppDatabase):
    document = await db.exec_query(Queries.get_document_query(document_id))
    if document is None or document.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    
    Path(document.path).unlink(missing_ok=True)
    await db.exec_query(Queries.delete_document_query(document_id), returning=False)
