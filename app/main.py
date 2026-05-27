import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db, SessionLocal
from app.bot import engine as bot_engine
from app.routers import bot, analytics, portfolio

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    bot_engine.set_session_factory(SessionLocal)
    yield
    bot_engine.stop_bot()


app = FastAPI(title="Tinkoff Trading Bot", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bot.router,       prefix="/api/bot",       tags=["bot"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(portfolio.router, prefix="/api/portfolio",  tags=["portfolio"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
