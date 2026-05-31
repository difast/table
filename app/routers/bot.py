from fastapi import APIRouter
from app.bot import engine
from app.storage import load_config, save_config
from app.schemas import StatusOut, BotConfigIn, BotConfigOut

router = APIRouter()


@router.get("/status", response_model=StatusOut)
def get_status():
    return engine.get_state()


@router.post("/start")
def start():
    cfg = load_config()
    if not cfg.get("api_token"):
        return {"ok": False, "error": "API token not configured"}
    ok = engine.start_bot()
    if ok:
        cfg["active"] = True
        save_config(cfg)
    return {"ok": ok, "message": "Bot started" if ok else "Already running"}


@router.post("/stop")
def stop():
    ok = engine.stop_bot()
    if ok:
        cfg = load_config()
        cfg["active"] = False
        save_config(cfg)
    return {"ok": ok, "message": "Bot stopped" if ok else "Not running"}


@router.get("/config", response_model=BotConfigOut)
def get_config():
    cfg = load_config()
    return {
        "mode": cfg["mode"],
        "strategy": cfg["strategy"],
        "active": cfg["active"],
        "instruments": cfg["instruments"],
        "account_id": cfg["account_id"],
        "strategy_params": cfg["strategy_params"],
        "candle_interval": cfg["candle_interval"],
        "tick_interval_sec": cfg["tick_interval_sec"],
        "has_token": bool(cfg.get("api_token")),
        "token_preview": (cfg["api_token"][:6] + "***") if len(cfg.get("api_token","")) > 6 else ("***" if cfg.get("api_token") else ""),
    }


@router.post("/config")
def update_config(body: BotConfigIn):
    cfg = load_config()
    data = body.model_dump(exclude_none=True)
    for key, val in data.items():
        if key == "strategy_params" and isinstance(val, dict):
            for s, p in val.items():
                cfg["strategy_params"].setdefault(s, {}).update(p)
        else:
            cfg[key] = val
    save_config(cfg)
    return {"ok": True}


@router.get("/strategies")
def list_strategies():
    return {
        "strategies": [
            {
                "id": "rsi",
                "name": "RSI",
                "description": "Покупка при выходе RSI из зоны перепроданности, продажа из зоны перекупленности",
                "params": ["period", "overbought", "oversold", "quantity"],
            },
            {
                "id": "macd",
                "name": "MACD",
                "description": "Покупка при пересечении MACD гистограммы с нуля вверх, продажа — вниз",
                "params": ["fast", "slow", "signal", "quantity"],
            },
            {
                "id": "bollinger",
                "name": "Bollinger Bands",
                "description": "Покупка при пробое нижней полосы вверх, продажа при пробое верхней вниз",
                "params": ["period", "std_dev", "quantity"],
            },
            {
                "id": "scalping",
                "name": "Scalping (EMA)",
                "description": "Покупка при пересечении быстрой EMA(9) выше медленной EMA(21), продажа — ниже",
                "params": ["fast", "slow", "quantity"],
            },
        ]
    }
