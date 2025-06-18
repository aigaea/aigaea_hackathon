import os
import sys
import json

from cryptography.fernet import Fernet
from dotenv import find_dotenv, load_dotenv, get_key, set_key


def get_envsion(key, format=True):
    if format:
        value = []
        valueStr = get_key(find_dotenv(".env"), key_to_get=key)
        if valueStr != None:
            value = valueStr.split(",")
    else:
        value = get_key(find_dotenv(".env"), key_to_get=key)
    return value


def set_envsion(key, value, format=True):
    if format:
        valueStr = ",".join(value)
    else:
        valueStr = value
    return set_key(find_dotenv(".env"), key_to_set=key, value_to_set=valueStr)


if not os.path.exists(".env"):
    print("ERROR: '.env' file does not exist")
    sys.exit()

load_dotenv(find_dotenv(".env"))

## FastAPI
FASTAPI_API_PATH: str = "/api"
FASTAPI_TITLE: str = "AIGAEA"
FASTAPI_VERSION: str = "0.0.1"
FASTAPI_DESCRIPTION: str = "AIGAEA API Interface"
FASTAPI_DOCS_URL: str | None = f"{FASTAPI_API_PATH}/docs"
FASTAPI_REDOC_URL: str | None = None  # f'{FASTAPI_API_PATH}/redoc'
FASTAPI_OPENAPI_URL: str | None = f"{FASTAPI_API_PATH}/openapi"
FASTAPI_STATIC_FILES: bool = False

ENVIRONMENT = os.getenv("ENVIRONMENT", default="127.0.0.1")
if ENVIRONMENT == "prod":
    FASTAPI_DOCS_URL = None
    FASTAPI_REDOC_URL = None
    FASTAPI_OPENAPI_URL = None

## UVICORN
UVICORN_HOST = os.getenv("UVICORN_HOST", default="127.0.0.1")
UVICORN_PORT = int(os.getenv("UVICORN_PORT", default=8000))

## CRYPTO-KEY
KEY = os.getenv("KEY")
KEY = KEY if KEY.endswith("=") else KEY + "="
FNet = Fernet(KEY)

## APP Configuration
GAEA_API_BASE_URL = os.getenv("GAEA_API_BASE_URL", default="https://api.aigaea.net/")
GAEA_API_BASE_URL = (GAEA_API_BASE_URL[:-1] if GAEA_API_BASE_URL.endswith("/") else GAEA_API_BASE_URL)
GAEA_APP_BASE_URL = os.getenv("GAEA_APP_BASE_URL", default="https://app.aigaea.net/")
GAEA_APP_BASE_URL = (GAEA_APP_BASE_URL[:-1] if GAEA_APP_BASE_URL.endswith("/") else GAEA_APP_BASE_URL)

APP_CONFIG = {
    "apibase": GAEA_API_BASE_URL,
    "appbase": GAEA_APP_BASE_URL,
    "error": f"{GAEA_APP_BASE_URL}/error?error=",
    "referral": f"{GAEA_APP_BASE_URL}/register?ref=",
    "redirect": f"{GAEA_APP_BASE_URL}/redirect?token=",
    "mission": f"{GAEA_APP_BASE_URL}/missions",
    "key": KEY,
}

## MySQL Configuration
MYSQL_MASTER = os.getenv("MYSQL_MASTER", default="127.0.0.1")
MYSQL_SLAVE = os.getenv("MYSQL_SLAVE", default="127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", default=3306))
MYSQL_USERNAME = os.getenv("MYSQL_USERNAME", default="root")
MYSQL_ENCRYPT = os.getenv("MYSQL_PASSWORD", default=None)
MYSQL_PASSWORD = FNet.decrypt(MYSQL_ENCRYPT.encode()).decode()
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", default="gaea_hackathon")
MYSQL_MAXCONNECT = int(os.getenv("MYSQL_MAXCONNECT", default=1000))
DB_CONFIG = {
    "master": MYSQL_MASTER,
    "slave": MYSQL_SLAVE,
    "port": MYSQL_PORT,
    "username": MYSQL_USERNAME,
    "password": MYSQL_PASSWORD,
    "database": MYSQL_DATABASE,
    "max_connect": MYSQL_MAXCONNECT,
}

## REDIS Configuration
REDIS_MODE = os.getenv("REDIS_MODE", default="standalone")
REDIS_MASTER = os.getenv("REDIS_MASTER", default="127.0.0.1:6379")
REDIS_SLAVE = os.getenv("REDIS_SLAVE", default="127.0.0.1:6379")
REDIS_USERNAME = os.getenv("REDIS_USERNAME", default=None)
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", default=None)
REDIS_DB = int(os.getenv("REDIS_DB", default=0))
REDIS_TIMEOUT = int(os.getenv("REDIS_TIMEOUT", default=5))
REDIS_CONFIG = {
    "mode": REDIS_MODE,
    "master": REDIS_MASTER,
    "slave": REDIS_SLAVE,
    "username": REDIS_USERNAME,
    "password": REDIS_PASSWORD,
    "db": REDIS_DB,
    "timeout": REDIS_TIMEOUT,
}

# AI
AI_AGENT_PROMPT=os.getenv("AI_AGENT_PROMPT", default="")
AI_API_CONFIG = os.getenv("AI_API_CONFIG", default="")
AI_CONFIG: list = json.loads(AI_API_CONFIG)

# web3
WEB3_NETWORK = os.getenv("WEB3_NETWORK", default="Base Sepolia")
WEB3_CONFIG = os.getenv("WEB3_CONFIG", default="")
# print(f"WEB3_CONFIG: {WEB3_CONFIG}")

# white prikey
web3_configs: list = json.loads(WEB3_CONFIG)
for web3_client in web3_configs:
    if web3_client['network'] == WEB3_NETWORK:
        WEB3_NETWORK_CONFIG = web3_client
        break
WEB3_WHITE_ENCRYPT = WEB3_NETWORK_CONFIG['white_prikey']
WEB3_WHITE_PRIKEY = FNet.decrypt(WEB3_WHITE_ENCRYPT.encode()).decode()
if len(WEB3_WHITE_PRIKEY) != 64:
    print(f"WEB3_WHITE_PRIKEY Data anomalies")
    exit
