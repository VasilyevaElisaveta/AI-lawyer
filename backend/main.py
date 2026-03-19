import uvicorn
from typing import Annotated
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, Request, Depends, status
from pwdlib import PasswordHash
from dotenv import load_dotenv
from os import getenv

from Database import Database
from RequestModels import RegistrationRequestModel


API_PREFIX = "/api/v1"


async def get_password_hash(request: Request):
    return request.app.state.password_hash

async def get_database(request: Request):
    return request.app.state.db


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.password_hash = PasswordHash.recommended()
    app.state.db = Database()
    yield

    app.state.db.close()


app = FastAPI(lifespan=lifespan)


@app.post(API_PREFIX + "/register/", status_code=status.HTTP_200_OK)
async def register(user_data: Annotated[RegistrationRequestModel, Form()],
                   password_hash: Annotated[PasswordHash, Depends(get_password_hash)],
                   db: Annotated[Database, Depends(get_database)]):
    username = user_data.username
    password = user_data.password
    hashed_password = password_hash.hash(password)

    new_user_id = db.create_user(username, hashed_password)

    if new_user_id is None:
        return {"user_id": None}
    return {"user_id": new_user_id}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)