from typing import List, Dict, Any, Tuple
import ta
from .base import BaseStrategy, Signal


class ScalpingStrategy(BaseStrategy):
    name = "scalping"

    def generate_signal(self, candles: List[Dict]) -> Tuple[str, float]:
        df = self._to_df(candles)
        fast = int(self.params.get("fast", 9))
        slow = int(self.params.get("slow", 21))

        if len(df) < slow + 2:
            return Signal.HOLD, 0.0

        fast_ema = ta.trend.EMAIndicator(close=df["close"], window=fast).ema_indicator()
        slow_ema = ta.trend.EMAIndicator(close=df["close"], window=slow).ema_indicator()

        fast_cur  = float(fast_ema.iloc[-1])
        fast_prev = float(fast_ema.iloc[-2])
        slow_cur  = float(slow_ema.iloc[-1])
        slow_prev = float(slow_ema.iloc[-2])

        if fast_prev <= slow_prev and fast_cur > slow_cur:
            return Signal.BUY, fast_cur - slow_cur
        if fast_prev >= slow_prev and fast_cur < slow_cur:
            return Signal.SELL, fast_cur - slow_cur
        return Signal.HOLD, fast_cur - slow_cur

    def min_candles_required(self) -> int:
        return int(self.params.get("slow", 21)) + 5
