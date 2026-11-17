import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .init_db import init_db
from .config import settings
from .database import SessionLocal
from .services.csv_sync import sync_from_csv
from .routers import auth, admin, departments, delos, toms, drafts, external, documents

logger = logging.getLogger("uvicorn.error")

async def periodic_sync_loop():
    interval_sec = max(60, settings.sync_interval_hours * 3600)
    while True:
        await asyncio.sleep(interval_sec)
        try:
            async with SessionLocal() as db:
                result = await sync_from_csv(db)
                logger.info(f"[sync] periodic: {result}")
        except Exception as e:
            logger.error(f"[sync] periodic error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    
    logger.info("[sync] Запуск первичной синхронизации...")
    try:
        async with SessionLocal() as db:
            result = await sync_from_csv(db)
            logger.info(f"[sync] initial result: {result}")
    except Exception as e:
        logger.error(f"[sync] initial error: {e}")

    sync_task = asyncio.create_task(periodic_sync_loop())
    
    yield
    
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Опись API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(departments.router)
app.include_router(delos.router)
app.include_router(toms.router)
app.include_router(drafts.router)
app.include_router(external.router)
app.include_router(documents.router)

@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "Опись"}