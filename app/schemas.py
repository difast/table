from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime


class TradeOut(BaseModel):
    id: int
    timestamp: datetime
    instrument: str
    figi: str
    direction: str
    quantity: int
    price: float
    total: float
    currency: str
    strategy: str
    mode: str
    status: str
    order_id: str
    pnl: Optional[float]
    signal_value: Optional[float]

    class Config:
        from_attributes = True


class BotConfigIn(BaseModel):
    api_token: Optional[str] = None
    mode: Optional[str] = None
    strategy: Optional[str] = None
    instruments: Optional[List[str]] = None
    account_id: Optional[str] = None
    strategy_params: Optional[Dict[str, Any]] = None
    candle_interval: Optional[str] = None
    tick_interval_sec: Optional[int] = None


class BotConfigOut(BaseModel):
    mode: str
    strategy: str
    active: bool
    instruments: List[str]
    account_id: str
    strategy_params: Dict[str, Any]
    candle_interval: str
    tick_interval_sec: int
    has_token: bool
    token_preview: str


class StatusOut(BaseModel):
    active: bool
    strategy: str
    mode: str
    account_id: str
    last_tick: Optional[str]
    last_error: Optional[str]
    uptime_sec: Optional[int]
    trades_today: int


class PnlPeriod(BaseModel):
    period: str
    from_date: Optional[str] = None
    to_date: Optional[str] = None


class PnlEntry(BaseModel):
    label: str
    pnl: float
    trades: int


class PortfolioPosition(BaseModel):
    figi: str
    instrument: str
    quantity: int
    avg_price: float
    current_price: float
    value: float
    pnl: float
    pnl_pct: float
    currency: str


class InstrumentInfo(BaseModel):
    figi: str
    ticker: str
    name: str
    currency: str
    instrument_type: str
