from typing import List, Dict, Any, Tuple
import ta
from .base import BaseStrategy, Signal


class BollingerStrategy(BaseStrategy):
    name = "bollinger"

    def generate_signal(self, candles: List[Dict]) -> Tuple[str, float]:
        df = self._to_df(candles)
        period  = int(self.params.get("period", 20))
        std_dev = float(self.params.get("std_dev", 2.0))

        if len(df) < period + 1:
            return Signal.HOLD, 0.0

        bb = ta.volatility.BollingerBands(close=df["close"], window=period, window_dev=std_dev)
        upper = bb.bollinger_hband()
        lower = bb.bollinger_lband()

        close_cur  = float(df["close"].iloc[-1])
        close_prev = float(df["close"].iloc[-2])
        upper_cur  = float(upper.iloc[-1])
        lower_cur  = float(lower.iloc[-1])
        lower_prev = float(lower.iloc[-2])
        upper_prev = float(upper.iloc[-2])

        # Price crosses lower band upward → buy
        if close_prev <= lower_prev and close_cur > lower_cur:
            return Signal.BUY, close_cur
        # Price crosses upper band downward → sell
        if close_prev >= upper_prev and close_cur < upper_cur:
            return Signal.SELL, close_cur
        return Signal.HOLD, close_cur

    def min_candles_required(self) -> int:
        return int(self.params.get("period", 20)) + 5
