import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pwdlib import PasswordHash
from argparse import ArgumentParser

from user.endpoints import user_router
from db.Database import Database


V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.password_hash = PasswordHash.recommended()
    parser = ArgumentParser("Database configuration parser")
    parser.add_argument("--sync", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--detail", action="store_true")
    args = parser.parse_args()
    is_sync, reset, detail = args.sync, args.reset, args.detail

    app.state.db = Database(is_sync=is_sync, detail=detail)

    if reset:
        await app.state.db.reset()

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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)