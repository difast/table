from typing import List, Dict, Any, Tuple
import ta
from .base import BaseStrategy, Signal


class MACDStrategy(BaseStrategy):
    name = "macd"

    def generate_signal(self, candles: List[Dict]) -> Tuple[str, float]:
        df = self._to_df(candles)
        fast   = int(self.params.get("fast", 12))
        slow   = int(self.params.get("slow", 26))
        signal = int(self.params.get("signal", 9))

        if len(df) < slow + signal:
            return Signal.HOLD, 0.0

        macd_ind = ta.trend.MACD(close=df["close"], window_fast=fast, window_slow=slow, window_sign=signal)
        macd_line   = macd_ind.macd()
        signal_line = macd_ind.macd_signal()
        hist        = macd_ind.macd_diff()

        if len(hist.dropna()) < 2:
            return Signal.HOLD, 0.0

        hist_cur  = float(hist.iloc[-1])
        hist_prev = float(hist.iloc[-2])
        macd_val  = float(macd_line.iloc[-1])

        if hist_prev < 0 and hist_cur >= 0:
            return Signal.BUY, macd_val
        if hist_prev > 0 and hist_cur <= 0:
            return Signal.SELL, macd_val
        return Signal.HOLD, macd_val

    def min_candles_required(self) -> int:
        return int(self.params.get("slow", 26)) + int(self.params.get("signal", 9)) + 5
