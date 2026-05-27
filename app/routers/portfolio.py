from fastapi import APIRouter, Query
from typing import Optional
from app.storage import load_config
from app.bot.tinkoff import TinkoffClient

router = APIRouter()


@router.get("/")
async def get_portfolio():
    cfg = load_config()
    if not cfg.get("api_token"):
        return {"error": "API token not configured", "positions": []}
    if not cfg.get("account_id"):
        return {"error": "Account not selected", "positions": []}
    client = TinkoffClient(cfg["api_token"], cfg["mode"])
    try:
        positions = await client.get_portfolio(cfg["account_id"])
        return {"positions": positions, "mode": cfg["mode"]}
    except Exception as e:
        return {"error": str(e), "positions": []}


@router.get("/accounts")
async def get_accounts():
    cfg = load_config()
    if not cfg.get("api_token"):
        return {"error": "API token not configured", "accounts": []}
    client = TinkoffClient(cfg["api_token"], cfg["mode"])
    try:
        accounts = await client.get_accounts()
        return {"accounts": accounts}
    except Exception as e:
        return {"error": str(e), "accounts": []}


@router.get("/candles")
async def get_candles(
    figi: str = Query(...),
    interval: str = Query("1hour"),
):
    cfg = load_config()
    if not cfg.get("api_token"):
        return {"error": "API token not configured", "candles": []}
    client = TinkoffClient(cfg["api_token"], cfg["mode"])
    try:
        candles = await client.get_candles(figi, interval=interval, limit=100)
        return {"candles": candles, "figi": figi}
    except Exception as e:
        return {"error": str(e), "candles": []}


@router.get("/instruments/search")
async def search_instruments(q: str = Query(..., min_length=1)):
    cfg = load_config()
    if not cfg.get("api_token"):
        return {"error": "API token not configured", "instruments": []}
    client = TinkoffClient(cfg["api_token"], cfg["mode"])
    try:
        instruments = await client.search_instruments(q)
        return {"instruments": instruments}
    except Exception as e:
        return {"error": str(e), "instruments": []}
