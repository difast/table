from typing import List, Dict, Any, Tuple
import pandas as pd
import ta
from .base import BaseStrategy, Signal


class RSIStrategy(BaseStrategy):
    name = "rsi"

    def generate_signal(self, candles: List[Dict]) -> Tuple[str, float]:
        df = self._to_df(candles)
        period = int(self.params.get("period", 14))
        overbought = float(self.params.get("overbought", 70))
        oversold = float(self.params.get("oversold", 30))

        if len(df) < period + 1:
            return Signal.HOLD, 0.0

        rsi_series = ta.momentum.RSIIndicator(close=df["close"], window=period).rsi()
        rsi = float(rsi_series.iloc[-1])
        rsi_prev = float(rsi_series.iloc[-2])

        if rsi_prev < oversold and rsi >= oversold:
            return Signal.BUY, rsi
        if rsi_prev > overbought and rsi <= overbought:
            return Signal.SELL, rsi
        return Signal.HOLD, rsi

    def min_candles_required(self) -> int:
        return int(self.params.get("period", 14)) + 5
