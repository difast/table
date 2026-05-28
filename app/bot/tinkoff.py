"""
Async REST client for Tinkoff Invest API v2.
Uses httpx — no gRPC SDK required.
Docs: https://tinkoff.github.io/investAPI/
"""
from __future__ import annotations
import httpx
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

SANDBOX_URL = "https://sandbox-invest-public-api.tinkoff.ru/rest"
LIVE_URL    = "https://invest-public-api.tinkoff.ru/rest"

CANDLE_INTERVALS = {
    "1min":  "CANDLE_INTERVAL_1_MIN",
    "5min":  "CANDLE_INTERVAL_5_MIN",
    "15min": "CANDLE_INTERVAL_15_MIN",
    "1hour": "CANDLE_INTERVAL_HOUR",
    "1day":  "CANDLE_INTERVAL_DAY",
}

CANDLE_LOOKBACK = {
    "1min":  timedelta(hours=2),
    "5min":  timedelta(hours=10),
    "15min": timedelta(days=2),
    "1hour": timedelta(days=7),
    "1day":  timedelta(days=100),
}


def _q(obj: dict | None) -> float:
    if not obj:
        return 0.0
    return float(obj.get("units", 0)) + obj.get("nano", 0) / 1e9


def _to_q(value: float) -> dict:
    units = int(value)
    nano = round((value - units) * 1_000_000_000)
    return {"units": str(units), "nano": nano}


def _fmt_dt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TinkoffClient:
    def __init__(self, token: str, mode: str = "sandbox"):
        self.token = token
        self.mode  = mode
        self.base  = SANDBOX_URL if mode == "sandbox" else LIVE_URL

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type":  "application/json",
        }

    async def _post(self, service: str, method: str, body: dict = None) -> dict:
        url = f"{self.base}/tinkoff.public.invest.api.contract.v1.{service}/{method}"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, headers=self._headers(), json=body or {})
            r.raise_for_status()
            return r.json()

    async def _sandbox(self, method: str, body: dict = None) -> dict:
        return await self._post("SandboxService", method, body)

    # ------------------------------------------------------------------ accounts

    async def get_accounts(self) -> List[Dict[str, Any]]:
        if self.mode == "sandbox":
            data = await self._sandbox("GetSandboxAccounts")
        else:
            data = await self._post("UsersService", "GetAccounts")
        return [
            {"id": a.get("id", ""), "name": a.get("name", ""), "type": a.get("type", "")}
            for a in data.get("accounts", [])
        ]

    async def ensure_sandbox_account(self) -> str:
        accounts = await self.get_accounts()
        if accounts:
            return accounts[0]["id"]
        data = await self._sandbox("OpenSandboxAccount")
        return data.get("accountId", "")

    # ------------------------------------------------------------------ portfolio

    async def get_portfolio(self, account_id: str) -> List[Dict[str, Any]]:
        if self.mode == "sandbox":
            data = await self._sandbox("GetSandboxPortfolio", {"accountId": account_id})
        else:
            data = await self._post("OperationsService", "GetPortfolio", {"accountId": account_id})
        result = []
        for pos in data.get("positions", []):
            qty     = _q(pos.get("quantity"))
            avg     = _q(pos.get("averagePositionPrice"))
            cur     = _q(pos.get("currentPrice"))
            pnl     = _q(pos.get("expectedYield"))
            pnl_pct = (pnl / (avg * qty) * 100) if avg and qty else 0.0
            result.append({
                "figi":          pos.get("figi", ""),
                "instrument":    pos.get("figi", ""),
                "quantity":      qty,
                "avg_price":     avg,
                "current_price": cur,
                "value":         cur * qty,
                "pnl":           pnl,
                "pnl_pct":       round(pnl_pct, 2),
                "currency":      pos.get("averagePositionPrice", {}).get("currency", "RUB"),
            })
        return result

    # ------------------------------------------------------------------ market data

    async def get_candles(
        self,
        figi: str,
        interval: str = "1hour",
        from_dt: Optional[datetime] = None,
        to_dt:   Optional[datetime] = None,
        limit:   int = 100,
    ) -> List[Dict]:
        if not from_dt:
            from_dt = datetime.now(timezone.utc) - CANDLE_LOOKBACK.get(interval, timedelta(days=2))
        if not to_dt:
            to_dt = datetime.now(timezone.utc)

        data = await self._post("MarketDataService", "GetCandles", {
            "figi":     figi,
            "from":     _fmt_dt(from_dt),
            "to":       _fmt_dt(to_dt),
            "interval": CANDLE_INTERVALS.get(interval, "CANDLE_INTERVAL_HOUR"),
        })
        return [
            {
                "time":   c.get("time", ""),
                "open":   _q(c.get("open")),
                "high":   _q(c.get("high")),
                "low":    _q(c.get("low")),
                "close":  _q(c.get("close")),
                "volume": int(c.get("volume", 0)),
            }
            for c in data.get("candles", [])
        ]

    async def get_last_price(self, figis: List[str]) -> Dict[str, float]:
        data = await self._post("MarketDataService", "GetLastPrices", {"figi": figis})
        return {lp.get("figi", ""): _q(lp.get("price")) for lp in data.get("lastPrices", [])}

    # ------------------------------------------------------------------ orders

    async def place_order(
        self,
        account_id: str,
        figi: str,
        direction: str,
        quantity: int,
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        body = {
            "accountId": account_id,
            "figi":      figi,
            "quantity":  str(quantity),
            "direction": "ORDER_DIRECTION_BUY" if direction == "buy" else "ORDER_DIRECTION_SELL",
            "orderType": "ORDER_TYPE_MARKET" if price is None else "ORDER_TYPE_LIMIT",
            "orderId":   str(int(datetime.now().timestamp() * 1000)),
        }
        if price is not None:
            body["price"] = _to_q(price)

        if self.mode == "sandbox":
            data = await self._sandbox("PostSandboxOrder", body)
        else:
            data = await self._post("OrdersService", "PostOrder", body)

        exec_price = _q(data.get("executedOrderPrice")) or price or 0.0
        return {
            "order_id": data.get("orderId", ""),
            "status":   data.get("executionReportStatus", ""),
            "price":    exec_price,
            "total":    exec_price * quantity,
        }

    # ------------------------------------------------------------------ sandbox utils

    async def sandbox_topup(self, account_id: str, amount: float = 100000) -> dict:
        data = await self._sandbox("SandboxPayIn", {
            "accountId": account_id,
            "amount": {"currency": "rub", "units": str(int(amount)), "nano": 0},
        })
        return data

    # ------------------------------------------------------------------ instruments

    async def search_instruments(self, query: str) -> List[Dict[str, Any]]:
        data = await self._post("InstrumentsService", "FindInstrument", {"query": query})
        return [
            {
                "figi":            i.get("figi", ""),
                "ticker":          i.get("ticker", ""),
                "name":            i.get("name", ""),
                "currency":        i.get("currency", ""),
                "instrument_type": i.get("instrumentType", ""),
            }
            for i in data.get("instruments", [])[:20]
        ]
