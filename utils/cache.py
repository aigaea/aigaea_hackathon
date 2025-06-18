import asyncio
import json
from builtins import anext
from contextlib import asynccontextmanager

from utils.log import log as logger
from utils.redis.init import get_redis
from utils.serialization_tools import is_json, get_dict_target_value


@asynccontextmanager
async def get_redis_connection(master_db: bool | None = True):
    _c = get_redis(master_db)
    if _c is None:
        raise RuntimeError("Unable to connect to Redis: _c")
    cache = await anext(_c)
    if cache is None:
        raise RuntimeError("Unable to connect to Redis: cache")
    try:
        yield cache
    finally:
        pass


async def validate_key_and_data(cache, key: str):
    if not await cache.exists(key):
        return None
    data = await cache.get(key)
    if not data:
        return None
    return data


async def increment_redis_data(master_db: bool, key: str, value_key: str = None, **kwargs) -> bool:
    try:
        async with get_redis_connection(master_db) as cache:
            data = await validate_key_and_data(cache, key)
            if not data:
                return False
            # print(f"increment_redis_data key: {key} data: {data}")
            if is_json(data):
                data = json.loads(data)
                if value_key and int(get_dict_target_value(data, value_key)) >= 0:
                    data[value_key] += 1
                    data_json = json.dumps(data)
                    await cache.set(key, data_json, **kwargs)
            return True
    except Exception as e:
        logger.error(f"increment_redis_data Exception: {str(e)}")
        return False


async def get_redis_data(master_db: bool, key: str, value_key: str = None):
    try:
        async with get_redis_connection(master_db) as cache:
            data = await validate_key_and_data(cache, key)
            if not data:
                return None
            # print(f"get_redis_data {key} data: {data}")
            if is_json(data):
                data = json.loads(data)
                if value_key:
                    return get_dict_target_value(data, value_key)
            return data
    except Exception as e:
        logger.error(f"get_redis_data Exception: {str(e)}")
        return None


async def set_redis_data(master_db: bool, key: str, value=None, **kwargs):
    try:
        async with get_redis_connection(master_db) as cache:
            if isinstance(value, dict) or isinstance(value, list):
                value = json.dumps(value)
            # print(f"set_redis_data {key} value: {value}")
            await cache.set(key, value, **kwargs)
    except Exception as e:
        logger.error(f"set_redis_data Exception: {str(e)}")
        return None


async def del_redis_data(master_db: bool, key: str) -> bool:
    try:
        async with get_redis_connection(master_db) as cache:
            data = await validate_key_and_data(cache, key)
            if not data:
                return False
            await cache.delete(key)
            return True
    except Exception as e:
        logger.error(f"del_redis_data Exception: {str(e)}")
        return False


if __name__ == '__main__':
    asyncio.run(get_redis_data(True, 'sys:settings'))
