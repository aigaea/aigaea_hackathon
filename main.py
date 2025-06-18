import argparse
import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.router import router as api_router
from config import *
from utils.log import Loggers, log as logger

# argparse
parser = argparse.ArgumentParser()
parser.add_argument('-d', '--debug', type=bool, default=False, action=argparse.BooleanOptionalAction)
parser.add_argument('-l', '--log', type=str, default="warning")
args = parser.parse_args()
run_debug = bool(args.debug)
run_log = str(args.log.lower())
if run_debug:
    run_log = "DEBUG"

# log level
logger.remove()
logger.add(sys.stdout, level=str(run_log).upper())
Loggers.init_config()

app = FastAPI(
    title=FASTAPI_TITLE,
    version=FASTAPI_VERSION,
    description=FASTAPI_DESCRIPTION,
    docs_url=FASTAPI_DOCS_URL,
    redoc_url=FASTAPI_REDOC_URL,
    openapi_url=FASTAPI_OPENAPI_URL,
)

## middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
## router
app.include_router(api_router)


@app.get("/")
async def index():
    return {"message": "Hello World"}


if __name__ == "__main__":
    cpu_count = 1 if run_debug else os.cpu_count() or 1
    print(f"cpu_count: {cpu_count}")
    uvicorn.run(app="main:app", host=UVICORN_HOST, port=UVICORN_PORT, reload=run_debug, workers=cpu_count, limit_concurrency=2000)
