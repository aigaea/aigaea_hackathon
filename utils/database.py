import aiomysql
import sys
from fastapi import HTTPException, Depends
from jose import JWTError

from utils.log import log as logger
from config import DB_CONFIG

# Database configuration
DATABASE_CONFIG = {
    "host": DB_CONFIG['master'],
    "port": DB_CONFIG['port'],
    "user": DB_CONFIG['username'],
    "password": DB_CONFIG['password'],
    "db": DB_CONFIG['database'],
    "autocommit": True,
    "minsize": 1,
    "maxsize": DB_CONFIG['max_connect'],
    "connect_timeout": 10,
    "pool_recycle": 60,
    "echo": False
}

# Create a database connection pool
async def get_db_pool():
    try:
        pool = await aiomysql.create_pool(**DATABASE_CONFIG)
        if pool is None:
            logger.error(f"ERROR: Database connection failed")
            sys.exit()
        return pool
    except Exception as e:
        logger.error(f"get_db_pool() except ERROR: {str(e)}")
        return None

# Dependency to inject database connection pool
async def get_db(pool = Depends(get_db_pool)):
    frequently_exception = HTTPException(status_code=503, detail="Service Unavailable")
    credentials_exception = HTTPException(status_code=401, detail="Invalid JWT Token")
    try:
        if pool is None:
            logger.error(f"get_db() pool is None")
            raise frequently_exception
            yield None
        
        async with pool.acquire() as connection:
            if not connection:
                raise frequently_exception
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                yield cursor
    except JWTError:
        raise credentials_exception
    except Exception as e:
        logger.error(f"get_db() except ERROR: {str(e)}")
        raise frequently_exception

DATABASE_CONFIG_SLAVE = {
    "host": DB_CONFIG['slave'],
    "port": DB_CONFIG['port'],
    "user": DB_CONFIG['username'],
    "password": DB_CONFIG['password'],
    "db": DB_CONFIG['database'],
    "autocommit": True,
    "minsize": 1,
    "maxsize": DB_CONFIG['max_connect'],
    "connect_timeout": 10,
    "pool_recycle": 60,
    "echo": False
}

# Create a database connection pool
async def get_db_pool_slave():
    try:
        pool = await aiomysql.create_pool(**DATABASE_CONFIG_SLAVE)
        if pool is None:
            logger.error(f"ERROR: Database connection failed")
            sys.exit()
        return pool
    except Exception as e:
        logger.error(f"get_db_pool_slave() except ERROR: {str(e)}")
        return None

# Dependency to inject database connection pool
async def get_db_slave(pool = Depends(get_db_pool_slave)):
    frequently_exception = HTTPException(status_code=503, detail="Service Unavailable")
    credentials_exception = HTTPException(status_code=401, detail="Invalid JWT Token")
    try:
        if pool is None:
            logger.error(f"get_db_slave() pool is None")
            raise frequently_exception
            yield None
        
        async with pool.acquire() as connection:
            if not connection:
                raise frequently_exception
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                yield cursor
    except JWTError:
        raise credentials_exception
    except Exception as e:
        logger.error(f"get_db_slave() except ERROR: {str(e)}")
        raise frequently_exception
