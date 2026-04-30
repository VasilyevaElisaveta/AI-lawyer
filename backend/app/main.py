import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pwdlib import PasswordHash
from argparse import ArgumentParser
from dotenv import load_dotenv
from os import getenv

from user.queries import Queries
from user.endpoints import user_router
from chat.endpoints import chat_router
from documents.endpoints import documents_router
from admin.endpoints import admin_router
from db.Database import Database


load_dotenv()


V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.password_hash = PasswordHash.recommended()
    parser = ArgumentParser("Database configuration parser")
    parser.add_argument("--sync", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--detail", action="store_true")
    parser.add_argument("--temp", action="store_true")
    args = parser.parse_args()
    is_sync, reset, detail, is_temp = args.sync, args.reset, args.detail, args.temp

    app.state.db = Database(is_sync=is_sync, is_temp=is_temp, detail=detail)

    if reset:
        await app.state.db.reset()

    admin_username = getenv("admin_username")

    if admin_username is not None:
        admin = await app.state.db.exec_query(Queries.get_user_query(admin_username))

        if admin is None:
            admin_email = getenv("admin_email")
            admin_password = getenv("admin_password")
            admin_name = getenv("admin_name")
            admin_surname = getenv("admin_surname")

            admin_password_hash = app.state.password_hash.hash(admin_password)

            await app.state.db.exec_query(
                Queries.create_user_query(
                    username=admin_username,
                    email=admin_email,
                    hashed_password=admin_password_hash,
                    name=admin_name,
                    surname=admin_surname,
                    is_admin=True
                    )
                )

    yield

    app.state.db.close()


app = FastAPI(
    lifespan=lifespan,
    docs_url=V1_PREFIX + "/docs",
    openapi_url=V1_PREFIX + "/openapi.json"
)

origins = [
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(user_router, prefix=V1_PREFIX)
app.include_router(chat_router, prefix=V1_PREFIX)
app.include_router(documents_router, prefix=V1_PREFIX)
app.include_router(admin_router, prefix=V1_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
