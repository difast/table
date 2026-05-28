import json
import os
from typing import Any, Dict
from app.config import settings

_defaults: Dict[str, Any] = {
    "api_token": "",
    "mode": "sandbox",       # sandbox | live
    "strategy": "rsi",       # rsi | macd | bollinger
    "active": False,
    "instruments": [],       # list of FIGIs
    "account_id": "",
    "strategy_params": {
        "rsi": {"period": 14, "overbought": 70, "oversold": 30, "quantity": 1},
        "macd": {"fast": 12, "slow": 26, "signal": 9, "quantity": 1},
        "bollinger": {"period": 20, "std_dev": 2.0, "quantity": 1},
        "scalping": {"fast": 9, "slow": 21, "quantity": 1},
    },
    "candle_interval": "1min",  # 1min | 5min | 15min | 1hour | 1day
    "tick_interval_sec": 60,
}


def _ensure_dir():
    os.makedirs(settings.data_dir, exist_ok=True)


def load_config() -> Dict[str, Any]:
    _ensure_dir()
    if not os.path.exists(settings.bot_config_path):
        return dict(_defaults)
    try:
        with open(settings.bot_config_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        cfg = dict(_defaults)
        cfg.update(saved)
        # Deep merge strategy_params
        for k, v in _defaults["strategy_params"].items():
            if k not in cfg["strategy_params"]:
                cfg["strategy_params"][k] = dict(v)
        return cfg
    except Exception:
        return dict(_defaults)


def save_config(cfg: Dict[str, Any]) -> None:
    _ensure_dir()
    tmp = settings.bot_config_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, settings.bot_config_path)
