from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routes import applications, board, dashboard, exports, imports


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Job Application Tracker", lifespan=lifespan)
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "static")),
    name="static",
)
app.include_router(dashboard.router)
app.include_router(applications.router)
app.include_router(board.router)
app.include_router(exports.router)
app.include_router(imports.router)
