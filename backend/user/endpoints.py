from typing import Annotated
from fastapi import APIRouter, Form, Body, status, HTTPException

from user.tokenService import TokenService
from user.queries import Queries
from user.RequestModels import (RegistrationRequestModel, LoginRequestModel,
                                UserResponseModel, TokensResponseModel,
                                RefreshTokensRequest, UpdateInfoRequestModel,
                                ChangePasswordRequestModel, DeleteUserRequest)

from dependencies.dependencies import CurrentUser, AppDatabase, AppPasswordHash



user_router = APIRouter(prefix="/user", tags=["user"])


@user_router.post("/register/",
                  description="Registration for new users.",
                  response_model=UserResponseModel,
                  status_code=status.HTTP_201_CREATED)
async def register(user_data: Annotated[RegistrationRequestModel, Form()], password_hash: AppPasswordHash, db: AppDatabase):
    if not user_data.user_agreement_accepted or not user_data.user_agreement_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user must accept the user agreement and the personal data processing policy before registration."
        )

    current_user_by_username = await db.exec_query(Queries.get_user_query(user_data.username))
    if current_user_by_username is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with username {user_data.username} already exists."
        )

    current_user_by_email = await db.exec_query(Queries.get_user_query(user_data.email, by_username=False))
    if current_user_by_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {user_data.email} already exists."
        )
    
    password = user_data.password
    hashed_password = password_hash.hash(password)
    return await db.exec_query(
        Queries.create_user_query(
            username=user_data.username, email=user_data.email, 
            hashed_password=hashed_password, name=user_data.name,
            surname=user_data.surname, patronymic=user_data.patronymic
        )
    )
    

@user_router.post("/login/",
          description="Login with password and username",
          response_model=TokensResponseModel,
          status_code=status.HTTP_200_OK)
async def login(user_data: Annotated[LoginRequestModel, Form()], password_hash: AppPasswordHash, db: AppDatabase):
    success_login = True
    current_user = await db.exec_query(Queries.get_user_query(user_data.username))

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
async def refresh_tokens(user_data: Annotated[RefreshTokensRequest, Body()], db: AppDatabase):
    token_bytes = user_data.token.encode("utf-8")
    username = TokenService.decode_token(token_bytes, "refresh")
    current_user = await db.exec_query(Queries.get_user_query(username))
    if current_user is None:
        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Indalid token.",
                headers={"WWW-Authenticate": "Bearer"}
            )
    token_pair = TokenService.get_token_pair(current_user.username)
    token_pair.update({"token_type": "bearer"})
    return token_pair


@user_router.get("/me/",
                 description="Get the current user.",
                 response_model=UserResponseModel,
                 status_code=status.HTTP_200_OK)
async def get_user(user: CurrentUser):
    return user


@user_router.put("/me/update-info/",
                 description="Update user info.",
                 response_model=UpdateInfoRequestModel,
                 status_code=status.HTTP_200_OK)
async def update_user_data(user_data: Annotated[UpdateInfoRequestModel, Form()], user: CurrentUser, db: AppDatabase):
    updated_user = await db.exec_query(Queries.update_user_query(user.id, user_data.model_dump()))
    return updated_user


@user_router.put("/me/change-password/",
                 description="Change the current user password.",
                 status_code=status.HTTP_200_OK)
async def change_password(data: Annotated[ChangePasswordRequestModel, Form()], user: CurrentUser, db: AppDatabase, password_hash: AppPasswordHash):
    old_password, new_password = data.old_password, data.new_password

    if not password_hash.verify(old_password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="The old password is incorrect.")
    
    new_password_hash = password_hash.hash(new_password)

    await db.exec_query(Queries.change_password_query(user.id, new_password_hash), returning=False)


@user_router.delete("/me/delete/",
                    description="Delete the current user account.",
                    status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(data: Annotated[DeleteUserRequest, Form()], user: CurrentUser, db: AppDatabase):
    confirmation = data.confirmation

    if not confirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user should confirm the account deletion."
        )
    
    await db.exec_query(Queries.delete_user_query(user.id), returning=False)
