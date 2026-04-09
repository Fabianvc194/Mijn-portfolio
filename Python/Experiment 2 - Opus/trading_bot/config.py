"""
config.py – Centraliseerde configuratie, geladen uit environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Bitvavo
    BITVAVO_API_KEY: str = os.environ["BITVAVO_API_KEY"]
    BITVAVO_API_SECRET: str = os.environ["BITVAVO_API_SECRET"]

    # Webhook HMAC
    WEBHOOK_SECRET: str = os.environ["WEBHOOK_SECRET"]

    # Risk defaults
    RISK_PCT: float = float(os.getenv("RISK_PCT", "2.0"))
    TRAILING_STOP_PCT: float = float(os.getenv("TRAILING_STOP_PCT", "3.0"))

    # Ondersteunde markten en hun specifieke regels
    MARKETS = {
        "BTC-EUR": {
            "order_type": "limit",
            "volatility_filter": False,
        },
        "ETH-EUR": {
            "order_type": "limit",
            "volatility_filter": True,
            "max_spread_pct": 0.1,  # blokkeer bij spread > 0.1 %
        },
    }
