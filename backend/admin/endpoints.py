from typing import Annotated
from fastapi import APIRouter, Form, Query, status, HTTPException

from user.queries import Queries as UserQueries
from user.RequestModels import UserResponseModel, UpdateInfoRequestModel, DeleteUserRequestModel

from admin.queries import Queries as AdminQueries
from admin.RequestModels import (MessagesRatingsModel, AppealTypesModel, ChangePasswordModel, AgentsRatingsModel,
                                 AgentsTypesModel, UserFiltersModel, MessageFiltersModel, UsersModel, MessagesModel)

from db.DatabaseModels import User
from dependencies.dependencies import CurrentUser, AppDatabase, AppPasswordHash


admin_router = APIRouter(prefix="/admin", tags=["admin"])


def is_admin(user: User, return_bool: bool=False):
    if return_bool:
        return user.is_admin
    else:
        if not user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User doesn't have access to this page.")


@admin_router.get("/messages/",
                  description="Get messages.",
                  response_model=MessagesModel,
                  status_code=status.HTTP_200_OK)
async def get_messages_statistics_quert(filters: Annotated[MessageFiltersModel, Query()], admin_user: CurrentUser, db: AppDatabase):
    is_admin(admin_user)

    messages = await db.exec_query(AdminQueries.get_messages_query(filters), one_or_none=False)
    return {"messages": messages}


@admin_router.get("/messages/ratings/",
                  description="Get each message rating amount.",
                  response_model=MessagesRatingsModel,
                  status_code=status.HTTP_200_OK)
async def get_messages_ratings_statistics_quert(admin_user: CurrentUser, db: AppDatabase):
    is_admin(admin_user)

    statistics = await db.exec_query(AdminQueries.get_messages_retings_amount_query(), one_or_none=False)
    return {"statistics": statistics}


@admin_router.get("/appeal_types/",
                  description="Get each appeal type amount.",
                  response_model=AppealTypesModel,
                  status_code=status.HTTP_200_OK)
async def get_appeal_types_statistics_quert(admin_user: CurrentUser, db: AppDatabase):
    is_admin(admin_user)

    statistics = await db.exec_query(AdminQueries.get_appeal_types_amount_query(), one_or_none=False)
    return {"statistics": statistics}


@admin_router.get("/agent_type/",
                  description="Get each appeal type amount.",
                  response_model=AgentsTypesModel,
                  status_code=status.HTTP_200_OK)
async def get_agent_type_statistics_query(admin_user: CurrentUser, db: AppDatabase):
    is_admin(admin_user)

    statistics = await db.exec_query(AdminQueries.get_agents_types_query(), one_or_none=False)
    return {"statistics": statistics}
    

@admin_router.get("/agent-rating/",
                  description="Get each appeal type amount.",
                  response_model=AgentsRatingsModel,
                  status_code=status.HTTP_200_OK)
async def get_agent_rating(admin_user: CurrentUser, db: AppDatabase):
    is_admin(admin_user)

    statistics = await db.exec_query(AdminQueries.get_agents_ratings_query(), one_or_none=False)
    return {"statistics": statistics}
    

@admin_router.get("/users/",
                  description="Get users.",
                  response_model=UsersModel,
                  status_code=status.HTTP_200_OK)
async def get_users(filters: Annotated[UserFiltersModel, Query()], admin_user: CurrentUser, db: AppDatabase):
    is_admin(admin_user)

    users = await db.exec_query(AdminQueries.get_users_query(filters), one_or_none=False)
    return {"users": users}
    

@admin_router.get("/users/{username}/",
                  description="Get user data.",
                  response_model=UserResponseModel,
                  status_code=status.HTTP_200_OK)
async def get(username: str, admin_user: CurrentUser, db: AppDatabase):
    is_admin(admin_user)

    return await db.exec_query(UserQueries.get_user_query(username))

    
@admin_router.put("/users/{username}/",
                  description="Update user data.",
                  response_model=UserResponseModel,
                  status_code=status.HTTP_200_OK)
async def update_user_data(username: str, user_data: Annotated[UpdateInfoRequestModel, Form()], admin_user: CurrentUser, db: AppDatabase):
    is_admin(admin_user)

    user = await db.exec_query(UserQueries.get_user_query(username))
    if is_admin(user, return_bool=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can not change another admin data.")
    
    another_users = await db.exec_query(UserQueries.get_user_query(user_data.username))
    if another_users is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="There is another user with this username.")
    
    updated_user = await db.exec_query(UserQueries.update_user_query(user.id, user_data.model_dump()))
    return updated_user


@admin_router.put("/users/{username}/change-password/")
async def change_user_password(username: str, data: Annotated[ChangePasswordModel, Form()], 
                               admin_user: CurrentUser, db: AppDatabase, password_hash: AppPasswordHash):
    is_admin(admin_user)

    user = await db.exec_query(UserQueries.get_user_query(username))
    if is_admin(user, return_bool=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can not change another admin data.")
    
    hashed_password = password_hash.hash(data.new_password)
    await db.exec_query(UserQueries.change_password_query(user.id, hashed_password), returning=False)
    

@admin_router.delete("/users/{username}/",
                     description="Delete user account.",
                     status_code=status.HTTP_204_NO_CONTENT)
async def detele_user(username: str, data: Annotated[DeleteUserRequestModel, Form()], admin_user: CurrentUser, db: AppDatabase):
    is_admin(admin_user)

    user = await db.exec_query(UserQueries.get_user_query(username))
    if is_admin(user, return_bool=True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can not delete another admin account.")

    if not data.confirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user should confirm the account deletion."
        )
    
    await db.exec_query(UserQueries.delete_user_query(user.id), returning=False)
