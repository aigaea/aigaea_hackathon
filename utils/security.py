import json
import time

from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from jose import JWTError
from loguru import logger

bearer = HTTPBearer()

async def get_current_address(authorization: HTTPAuthorizationCredentials = Depends(bearer)):
    credentials_exception = HTTPException(status_code=401, detail="Invalid address")
    try:
        eth_address = authorization.credentials
        if not (len(eth_address) == 42 and eth_address[:2] == '0x'): 
            logger.error(f"Invalid address - {eth_address}")
            raise credentials_exception

    except JWTError:
        raise credentials_exception
    return eth_address.lower()

