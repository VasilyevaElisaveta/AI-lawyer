import uvicorn
from typing import Annotated
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, Request, Depends, status, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib import PasswordHash
from argparse import ArgumentParser

from tokenService import TokenService
from Database import Database
from RequestModels import RegistrationRequestModel, LoginRequestModel, LoginResponseModel, UserResponseModel


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
auth_scheme = HTTPBearer()


@app.post(API_PREFIX + "/register/",
          description="Registration for new users.",
          status_code=status.HTTP_201_CREATED)
async def register(user_data: Annotated[RegistrationRequestModel, Form()],
                   password_hash: Annotated[PasswordHash, Depends(get_password_hash)],
                   db: Annotated[Database, Depends(get_database)]):
    current_user_by_username = await db.get_user(user_data.username, by_username=True)
    if current_user_by_username is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with username {user_data.username} already exists."
        )

    current_user_by_email = await db.get_user(user_data.email, by_username=False)
    if current_user_by_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {user_data.email} already exists."
        )
    
    password = user_data.password
    hashed_password = password_hash.hash(password)
    await db.create_user(user_data.username, user_data.email, hashed_password,
                         user_data.name, user_data.surname, user_data.patronymic)
    

@app.post(API_PREFIX + "/login/",
          description="Login with password and username",
          response_model=LoginResponseModel,
          status_code=status.HTTP_200_OK)
async def login(user_data: Annotated[LoginRequestModel, Form()],
                password_hash: Annotated[PasswordHash, Depends(get_password_hash)],
                db: Annotated[Database, Depends(get_database)]):
    success_login = True
    current_user = await db.get_user(user_data.username)

    if current_user is None:
        fake_hash= "fake hash"
        password_hash.verify(user_data.password, fake_hash)
        success_login = False
    if not password_hash.verify(user_data.password, current_user.password):
        success_login = False

    if not success_login:
        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

    token_pair = TokenService.get_token_pair(current_user.username)
    token_pair.update({"token_type": "bearer"})
    return token_pair


@app.get(API_PREFIX + "/me/",
         description="Get the current user.",
         response_model=UserResponseModel,
         status_code=status.HTTP_200_OK)
async def get_user(authorization_data: Annotated[HTTPAuthorizationCredentials, Depends(auth_scheme)], db: Annotated[Database, Depends(get_database)]):
    token = authorization_data.credentials
    username = TokenService.decode_token(token, "access")
    user = await db.get_user(username)
    return UserResponseModel(**user)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)