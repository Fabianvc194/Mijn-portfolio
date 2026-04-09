"""
exchange.py – Thin wrapper rond de python-bitvavo-api.

Verantwoordelijk voor:
  • verbinding beheren
  • balances opvragen
  • orderbook / ticker opvragen
  • orders plaatsen & annuleren
"""

from __future__ import annotations

import logging
from typing import Any

from python_bitvavo_api.bitvavo import Bitvavo

from config import Config

logger = logging.getLogger(__name__)


class Exchange:
    """Singleton-achtige wrapper; hergebruik hetzelfde object per process."""

    def __init__(self) -> None:
        self._client = Bitvavo(
            {
                "APIKEY": Config.BITVAVO_API_KEY,
                "APISECRET": Config.BITVAVO_API_SECRET,
                "RESTURL": "https://api.bitvavo.com/v2",
                "WSURL": "wss://ws.bitvavo.com/v2/",
                "ACCESSWINDOW": 10000,
                "DEBUGGING": False,
            }
        )

    # ------------------------------------------------------------------
    # Balances
    # ------------------------------------------------------------------
    def get_balance(self, asset: str = "EUR") -> float:
        """Haal beschikbaar saldo op voor een asset (default EUR)."""
        balances = self._client.balance({"symbol": asset})
        if isinstance(balances, dict) and "errorCode" in balances:
            raise RuntimeError(f"Bitvavo error: {balances}")
        for b in balances:
            if b["symbol"] == asset:
                return float(b["available"])
        return 0.0

    # ------------------------------------------------------------------
    # Marktdata
    # ------------------------------------------------------------------
    def get_ticker(self, market: str) -> dict[str, float]:
        """Retourneert {bid, ask, spread_pct}."""
        book = self._client.tickerBook({"market": market})
        if isinstance(book, dict) and "errorCode" in book:
            raise RuntimeError(f"Bitvavo error: {book}")
        bid = float(book["bid"])
        ask = float(book["ask"])
        mid = (bid + ask) / 2
        spread_pct = ((ask - bid) / mid) * 100 if mid > 0 else 999
        return {"bid": bid, "ask": ask, "spread_pct": spread_pct}

    def get_price(self, market: str) -> float:
        """Laatste prijs."""
        ticker = self._client.tickerPrice({"market": market})
        if isinstance(ticker, dict) and "errorCode" in ticker:
            raise RuntimeError(f"Bitvavo error: {ticker}")
        return float(ticker["price"])

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    def place_limit_order(
        self,
        market: str,
        side: str,
        amount: float,
        price: float,
    ) -> dict[str, Any]:
        """Plaats een limit order. side = 'buy' | 'sell'."""
        params = {
            "market": market,
            "side": side,
            "orderType": "limit",
            "amount": f"{amount}",
            "price": f"{price}",
            "timeInForce": "GTC",
        }
        result = self._client.placeOrder(
            params["market"],
            params["side"],
            params["orderType"],
            params,
        )
        if isinstance(result, dict) and "errorCode" in result:
            raise RuntimeError(f"Order mislukt: {result}")
        logger.info("Order geplaatst: %s", result)
        return result

    def cancel_order(self, market: str, order_id: str) -> dict[str, Any]:
        """Annuleer een open order."""
        result = self._client.cancelOrder(market, order_id)
        if isinstance(result, dict) and "errorCode" in result:
            raise RuntimeError(f"Cancel mislukt: {result}")
        logger.info("Order geannuleerd: %s %s", market, order_id)
        return result

    def get_open_orders(self, market: str) -> list[dict]:
        """Open orders voor een markt."""
        result = self._client.ordersOpen({"market": market})
        if isinstance(result, dict) and "errorCode" in result:
            raise RuntimeError(f"Open orders mislukt: {result}")
        return result
