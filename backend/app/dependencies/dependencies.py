from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request, Depends, status, HTTPException
from pwdlib import PasswordHash
from typing import Annotated

from db.Database import Database
from db.DatabaseModels import User
from user.tokenService import TokenService
from user.queries import Queries


auth_scheme = HTTPBearer()


async def get_password_hash(request: Request) -> PasswordHash:
    return request.app.state.password_hash

async def get_database(request: Request) -> Database:
    return request.app.state.db

async def get_current_user(authorization_data: Annotated[HTTPAuthorizationCredentials, Depends(auth_scheme)], db: Annotated[Database, Depends(get_database)]) -> User:
    token = authorization_data.credentials
    username = TokenService.decode_token(token, "access")
    current_user = await db.exec_query(Queries.get_user_query(username))
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not found.")
    return current_user


AppDatabase = Annotated[Database, Depends(get_database)]
AppPasswordHash = Annotated[PasswordHash, Depends(get_password_hash)]
CurrentUser = Annotated[User, Depends(get_current_user)]
