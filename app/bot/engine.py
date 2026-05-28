"""
Bot engine: runs the trading loop in a background asyncio task.
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.storage import load_config, save_config
from app.bot.tinkoff import TinkoffClient
from app.bot.strategies.rsi import RSIStrategy
from app.bot.strategies.macd import MACDStrategy
from app.bot.strategies.bollinger import BollingerStrategy
from app.bot.strategies.scalping import ScalpingStrategy
from app.bot.strategies.base import Signal

logger = logging.getLogger("bot.engine")

STRATEGIES = {
    "rsi": RSIStrategy,
    "macd": MACDStrategy,
    "bollinger": BollingerStrategy,
    "scalping": ScalpingStrategy,
}

# Shared state (in-process only, reset on restart)
state = {
    "active": False,
    "task": None,
    "last_tick": None,
    "last_error": None,
    "start_time": None,
    "trades_today": 0,
}

# Injected from main.py after DB is ready
_get_session = None


def set_session_factory(factory):
    global _get_session
    _get_session = factory


async def _save_trade(session, trade_data: dict):
    from app.models import Trade
    trade = Trade(**trade_data)
    session.add(trade)
    await session.commit()


async def _run_loop():
    logger.info("Bot loop started")
    while state["active"]:
        cfg = load_config()
        if not cfg.get("api_token") or not cfg.get("instruments"):
            logger.warning("No token or instruments configured, sleeping...")
            await asyncio.sleep(30)
            continue

        client = TinkoffClient(cfg["api_token"], cfg["mode"])
        account_id = cfg.get("account_id", "")

        if not account_id and cfg["mode"] == "sandbox":
            try:
                account_id = await client.ensure_sandbox_account()
                cfg["account_id"] = account_id
                save_config(cfg)
            except Exception as e:
                logger.error(f"Cannot get sandbox account: {e}")
                state["last_error"] = str(e)
                await asyncio.sleep(10)
                continue

        strategy_cls = STRATEGIES.get(cfg["strategy"], RSIStrategy)
        params = cfg["strategy_params"].get(cfg["strategy"], {})
        strategy = strategy_cls(params)
        interval = cfg.get("candle_interval", "1min")
        quantity = int(params.get("quantity", 1))

        for figi in cfg["instruments"]:
            if not state["active"]:
                break
            try:
                candles = await client.get_candles(figi, interval=interval, limit=strategy.min_candles_required() + 10)
                if not candles:
                    continue

                signal, indicator_val = strategy.generate_signal(candles)
                state["last_tick"] = datetime.now(timezone.utc).isoformat()
                state["last_error"] = None

                if signal == Signal.HOLD:
                    continue

                logger.info(f"Signal {signal} on {figi} (indicator={indicator_val:.4f})")
                last_price = candles[-1]["close"]

                order = await client.place_order(account_id, figi, signal, quantity)
                exec_price = order.get("price", last_price)

                if _get_session:
                    async with _get_session() as session:
                        await _save_trade(session, {
                            "instrument": figi,
                            "figi": figi,
                            "direction": signal,
                            "quantity": quantity,
                            "price": exec_price,
                            "total": exec_price * quantity,
                            "currency": "RUB",
                            "strategy": cfg["strategy"],
                            "mode": cfg["mode"],
                            "status": "executed",
                            "order_id": order.get("order_id", ""),
                            "signal_value": indicator_val,
                        })
                        state["trades_today"] += 1

            except Exception as e:
                logger.error(f"Error processing {figi}: {e}")
                state["last_error"] = str(e)

        tick_sec = int(cfg.get("tick_interval_sec", 60))
        await asyncio.sleep(tick_sec)

    logger.info("Bot loop stopped")


def start_bot():
    if state["active"]:
        return False
    state["active"] = True
    state["start_time"] = datetime.now(timezone.utc)
    state["trades_today"] = 0
    state["last_error"] = None
    loop = asyncio.get_event_loop()
    state["task"] = loop.create_task(_run_loop())
    return True


def stop_bot():
    if not state["active"]:
        return False
    state["active"] = False
    if state["task"]:
        state["task"].cancel()
        state["task"] = None
    return True


def get_state() -> dict:
    cfg = load_config()
    uptime = None
    if state["start_time"] and state["active"]:
        uptime = int((datetime.now(timezone.utc) - state["start_time"]).total_seconds())
    return {
        "active": state["active"],
        "strategy": cfg.get("strategy", "rsi"),
        "mode": cfg.get("mode", "sandbox"),
        "account_id": cfg.get("account_id", ""),
        "last_tick": state["last_tick"],
        "last_error": state["last_error"],
        "uptime_sec": uptime,
        "trades_today": state["trades_today"],
    }
