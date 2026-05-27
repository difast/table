from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd


class Signal:
    BUY  = "buy"
    SELL = "sell"
    HOLD = "hold"


class BaseStrategy(ABC):
    name: str = "base"

    def __init__(self, params: Dict[str, Any]):
        self.params = params

    @abstractmethod
    def generate_signal(self, candles: List[Dict]) -> tuple[str, float]:
        """Return (signal, indicator_value). signal is Signal.BUY/SELL/HOLD."""

    def _to_df(self, candles: List[Dict]) -> pd.DataFrame:
        df = pd.DataFrame(candles)
        df["close"] = df["close"].astype(float)
        df["high"]  = df["high"].astype(float)
        df["low"]   = df["low"].astype(float)
        df["open"]  = df["open"].astype(float)
        return df

    def min_candles_required(self) -> int:
        return 30
