import jwt
import datetime
from enum import StrEnum
from dotenv import load_dotenv
from os import getenv
from fastapi import HTTPException, status


load_dotenv()


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenService:

    __HASH = getenv("HASH", "hash")
    __ALGORITHM = getenv("ALGORITHM", "HS256")
    __ACCESS_TOKEN_EXPIRE_MINUTES = getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)
    __REFRESH_TOKEN_EXPIRE_MINUTES = getenv("REFRESH_TOKEN_EXPIRE_MINUTES", 90)

    @staticmethod
    def get_token_pair(sub: str) -> dict[str: str]:
        access_token = TokenService.create_token(sub)
        refresh_token = TokenService.create_token(sub, is_access=False)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    @staticmethod
    def create_token(sub: str, is_access: bool=True) -> str:
        if is_access:
            type = TokenType.ACCESS
            expires_time = TokenService.__ACCESS_TOKEN_EXPIRE_MINUTES
        else:
            type = TokenType.REFRESH
            expires_time=TokenService.__REFRESH_TOKEN_EXPIRE_MINUTES
        data = {
            "type": type,
            "sub": sub,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(int(expires_time))
        }
        token = jwt.encode(data, TokenService.__HASH, TokenService.__ALGORITHM)
        return token

    @staticmethod
    def decode_token(token: str, type: str) -> str | None:
        try:
            payload = jwt.decode(token, TokenService.__HASH, [TokenService.__ALGORITHM])
            token_type = TokenType(payload.get("type"))
            expected_token_type = TokenType(type)
            sub = payload.get("sub")
            if sub is None or token_type is not expected_token_type:
                raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail = "Could not validate credentials.",
                headers={"WWW-Authenticate": "Bearer"}
            )
            return sub
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Indalid token.",
                headers={"WWW-Authenticate": "Bearer"}
            )

    @staticmethod
    def refresh_token(token: str) -> str:
        sub = TokenService.decode_token(token, type="refresh")
        new_access_token = TokenService.create_token(sub)
        return new_access_token
