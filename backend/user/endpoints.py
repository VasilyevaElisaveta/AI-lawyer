from typing import Annotated
from fastapi import APIRouter, Form, Body, Depends, status, HTTPException
from pwdlib import PasswordHash

from user.tokenService import TokenService
from db.Database import Database
from db.DatabaseModels import User
from user.RequestModels import (RegistrationRequestModel, LoginRequestModel,
                                UserResponseModel, TokensResponseModel,
                                RefreshTokensRequest, UpdateInfoRequestModel,
                                ChangePasswordRequestModel, DeleteUserRequest)

from dependencies.dependencies import get_current_user, get_password_hash, get_database



user_router = APIRouter(prefix="/user", tags=["user"])


@user_router.post("/register/",
                  description="Registration for new users.",
                  response_model=UserResponseModel,
                  status_code=status.HTTP_201_CREATED)
async def register(user_data: Annotated[RegistrationRequestModel, Form()],
                   password_hash: Annotated[PasswordHash, Depends(get_password_hash)],
                   db: Annotated[Database, Depends(get_database)]):
    if not user_data.user_agreement_accepted or not user_data.user_agreement_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user must accept the user agreement and the personal data processing policy before registration."
        )

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
    return await db.create_user(user_data.username, user_data.email, hashed_password,
                                user_data.name, user_data.surname, user_data.patronymic)
    

@user_router.post("/login/",
          description="Login with password and username",
          response_model=TokensResponseModel,
          status_code=status.HTTP_200_OK)
async def login(user_data: Annotated[LoginRequestModel, Form()],
                password_hash: Annotated[PasswordHash, Depends(get_password_hash)],
                db: Annotated[Database, Depends(get_database)]):
    success_login = True
    current_user = await db.get_user(user_data.username)

    if current_user is None:
        fake_hash= password_hash.hash("fake hash")
        password_hash.verify(user_data.password, fake_hash)
        success_login = False
    elif not password_hash.verify(user_data.password, current_user.password):
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


@user_router.post("/refresh-tokens/",
                  description="Get a new pair of tokens using the refresh token.",
                  response_model=TokensResponseModel,
                  status_code=status.HTTP_200_OK)
async def refresh_tokens(data: Annotated[RefreshTokensRequest, Body()], db: Annotated[Database, Depends(get_database)]):
    token_bytes = data.token.encode("utf-8")
    username = TokenService.decode_token(token_bytes, "refresh")
    user = await db.get_user(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not found.")
    token_pair = TokenService.get_token_pair(user.username)
    token_pair.update({"token_type": "bearer"})
    return token_pair


@user_router.get("/me/",
                 description="Get the current user.",
                 response_model=UserResponseModel,
                 status_code=status.HTTP_200_OK)
async def get_user(user: Annotated[User, Depends(get_current_user)]):
    return user


@user_router.put("/me/update-info/",
                 description="Update user info.",
                 response_model=UpdateInfoRequestModel,
                 status_code=status.HTTP_200_OK)
async def update_user_data(user_data: Annotated[UpdateInfoRequestModel, Form()],
                           user: Annotated[User, Depends(get_current_user)],
                           db: Annotated[Database, Depends(get_database)]):
    updated_user = await db.update_user_info(user.id, user_data.model_dump())
    return updated_user


@user_router.put("/me/change-password/",
                 description="Change the current user password.",
                 status_code=status.HTTP_200_OK)
async def change_password(data: Annotated[ChangePasswordRequestModel, Form()],
                          user: Annotated[User, Depends(get_current_user)],
                          db: Annotated[Database, Depends(get_database)],
                          password_hash: Annotated[PasswordHash, Depends(get_password_hash)]):
    old_password, new_password = data.old_password, data.new_password

    if not password_hash.verify(old_password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="The old password is incorrect.")
    
    new_password_hash = password_hash.hash(new_password)

    await db.change_password(user.id, new_password_hash)


@user_router.delete("/me/delete/",
                    description="Delete the current user account.",
                    status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(data: Annotated[DeleteUserRequest, Form()],
                         user: Annotated[User, Depends(get_current_user)],
                         db: Annotated[Database, Depends(get_database)],):
    confirmation = data.confirmation

    if not confirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user should confirm the account deletion."
        )
    
    await db.delete_user(user.id)
