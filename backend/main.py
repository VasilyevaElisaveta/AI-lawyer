import uvicorn
from typing import Annotated
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, Request, Depends, status, HTTPException
from pwdlib import PasswordHash
from argparse import ArgumentParser

from Database import Database
from RequestModels import RegistrationRequestModel


API_PREFIX = "/api/v1"


async def get_password_hash(request: Request):
    return request.app.state.password_hash

async def get_database(request: Request) -> Database:
    return request.app.state.db


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


app = FastAPI(lifespan=lifespan)


@app.post(API_PREFIX + "/register/", status_code=status.HTTP_200_OK)
async def register(user_data: Annotated[RegistrationRequestModel, Form()],
                   password_hash: Annotated[PasswordHash, Depends(get_password_hash)],
                   db: Annotated[Database, Depends(get_database)]):
    current_user_by_username = await db.get_user(user_data.username, by_username=True)
    if current_user_by_username is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with username {user_data.username} already exists"
        )

    current_user_by_email = await db.get_user(user_data.email, by_username=False)
    if current_user_by_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {user_data.email} already exists"
        )
    
    password = user_data.password
    hashed_password = password_hash.hash(password)
    await db.create_user(user_data.username, user_data.email, hashed_password, user_data.name, user_data.surname, user_data.patronymic)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)