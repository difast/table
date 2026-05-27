"""
Thin async wrapper around tinkoff-invest-api SDK.
Handles sandbox / live switching transparently.
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any

from tinkoff.invest import (
    AsyncClient,
    CandleInterval,
    OrderDirection,
    OrderType,
    Quotation,
    InstrumentStatus,
    RequestError,
)
from tinkoff.invest.sandbox.client import SandboxAsyncClient

CANDLE_INTERVALS = {
    "1min":  CandleInterval.CANDLE_INTERVAL_1_MIN,
    "5min":  CandleInterval.CANDLE_INTERVAL_5_MIN,
    "15min": CandleInterval.CANDLE_INTERVAL_15_MIN,
    "1hour": CandleInterval.CANDLE_INTERVAL_HOUR,
    "1day":  CandleInterval.CANDLE_INTERVAL_DAY,
}


def _q_to_float(q: Quotation) -> float:
    return q.units + q.nano / 1e9


def _float_to_q(value: float) -> Quotation:
    units = int(value)
    nano = round((value - units) * 1e9)
    return Quotation(units=units, nano=nano)


def _client_cls(mode: str):
    return SandboxAsyncClient if mode == "sandbox" else AsyncClient


class TinkoffClient:
    def __init__(self, token: str, mode: str = "sandbox"):
        self.token = token
        self.mode = mode

    def _client(self):
        return _client_cls(self.mode)(self.token)

    async def get_accounts(self) -> List[Dict[str, Any]]:
        async with self._client() as c:
            if self.mode == "sandbox":
                resp = await c.sandbox.get_sandbox_accounts()
            else:
                resp = await c.users.get_accounts()
            return [
                {"id": a.id, "name": getattr(a, "name", ""), "type": str(a.type)}
                for a in resp.accounts
            ]

    async def ensure_sandbox_account(self) -> str:
        """Open a sandbox account if none exist; return account_id."""
        accounts = await self.get_accounts()
        if accounts:
            return accounts[0]["id"]
        async with self._client() as c:
            resp = await c.sandbox.open_sandbox_account()
            return resp.account_id

    async def get_portfolio(self, account_id: str) -> List[Dict[str, Any]]:
        async with self._client() as c:
            if self.mode == "sandbox":
                resp = await c.sandbox.get_sandbox_portfolio(account_id=account_id)
            else:
                resp = await c.operations.get_portfolio(account_id=account_id)
            result = []
            for pos in resp.positions:
                avg = _q_to_float(pos.average_position_price) if pos.average_position_price else 0
                cur = _q_to_float(pos.current_price) if pos.current_price else 0
                qty = _q_to_float(pos.quantity) if pos.quantity else 0
                pnl = _q_to_float(pos.expected_yield) if pos.expected_yield else 0
                pnl_pct = (pnl / (avg * qty) * 100) if avg and qty else 0
                result.append({
                    "figi": pos.figi,
                    "instrument": pos.figi,
                    "quantity": qty,
                    "avg_price": avg,
                    "current_price": cur,
                    "value": cur * qty,
                    "pnl": pnl,
                    "pnl_pct": round(pnl_pct, 2),
                    "currency": pos.average_position_price.currency if pos.average_position_price else "RUB",
                })
            return result

    async def get_candles(
        self,
        figi: str,
        interval: str = "1min",
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, float]]:
        if not from_dt:
            delta_map = {
                "1min": timedelta(hours=2),
                "5min": timedelta(hours=10),
                "15min": timedelta(days=2),
                "1hour": timedelta(days=7),
                "1day": timedelta(days=limit),
            }
            from_dt = datetime.now(timezone.utc) - delta_map.get(interval, timedelta(hours=2))
        if not to_dt:
            to_dt = datetime.now(timezone.utc)

        ci = CANDLE_INTERVALS.get(interval, CandleInterval.CANDLE_INTERVAL_1_MIN)
        async with self._client() as c:
            resp = await c.market_data.get_candles(figi=figi, from_=from_dt, to=to_dt, interval=ci)
            return [
                {
                    "time": candle.time.isoformat(),
                    "open": _q_to_float(candle.open),
                    "high": _q_to_float(candle.high),
                    "low": _q_to_float(candle.low),
                    "close": _q_to_float(candle.close),
                    "volume": candle.volume,
                }
                for candle in resp.candles
            ]

    async def get_last_price(self, figis: List[str]) -> Dict[str, float]:
        async with self._client() as c:
            resp = await c.market_data.get_last_prices(figi=figis)
            return {lp.figi: _q_to_float(lp.price) for lp in resp.last_prices}

    async def place_order(
        self,
        account_id: str,
        figi: str,
        direction: str,
        quantity: int,
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        order_dir = OrderDirection.ORDER_DIRECTION_BUY if direction == "buy" else OrderDirection.ORDER_DIRECTION_SELL
        order_type = OrderType.ORDER_TYPE_MARKET if price is None else OrderType.ORDER_TYPE_LIMIT

        async with self._client() as c:
            if self.mode == "sandbox":
                resp = await c.sandbox.post_sandbox_order(
                    account_id=account_id,
                    figi=figi,
                    quantity=quantity,
                    direction=order_dir,
                    order_type=order_type,
                    price=_float_to_q(price) if price else None,
                    order_id=str(int(datetime.now().timestamp() * 1000)),
                )
            else:
                resp = await c.orders.post_order(
                    account_id=account_id,
                    figi=figi,
                    quantity=quantity,
                    direction=order_dir,
                    order_type=order_type,
                    price=_float_to_q(price) if price else None,
                    order_id=str(int(datetime.now().timestamp() * 1000)),
                )
            executed_price = _q_to_float(resp.executed_order_price) if resp.executed_order_price else (price or 0)
            return {
                "order_id": resp.order_id,
                "status": str(resp.execution_report_status),
                "price": executed_price,
                "total": executed_price * quantity,
            }

    async def search_instruments(self, query: str) -> List[Dict[str, Any]]:
        async with self._client() as c:
            resp = await c.instruments.find_instrument(query=query)
            return [
                {
                    "figi": i.figi,
                    "ticker": i.ticker,
                    "name": i.name,
                    "currency": i.currency,
                    "instrument_type": i.instrument_type,
                }
                for i in resp.instruments[:20]
            ]
