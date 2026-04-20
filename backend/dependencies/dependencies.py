from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Request, Depends, status, HTTPException
from typing import Annotated

from db.Database import Database
from user.tokenService import TokenService


auth_scheme = HTTPBearer()


async def get_password_hash(request: Request):
    return request.app.state.password_hash

async def get_database(request: Request) -> Database:
    return request.app.state.db

async def get_current_user(authorization_data: Annotated[HTTPAuthorizationCredentials, Depends(auth_scheme)], db: Annotated[Database, Depends(get_database)]):
    token = authorization_data.credentials
    username = TokenService.decode_token(token, "access")
    user = await db.get_user(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not found.")
    return user