"""
security.py – Webhook authenticatie via SHA-256 HMAC.

TradingView stuurt de HMAC-signature mee in de HTTP-header
'X-Signature'.  De signature wordt berekend over de raw request
body met het gedeelde geheim (WEBHOOK_SECRET).
"""

from __future__ import annotations

import hashlib
import hmac
import logging

from config import Config

logger = logging.getLogger(__name__)


def compute_hmac(payload: bytes) -> str:
    """Bereken HMAC-SHA256 hex-digest van de payload."""
    return hmac.new(
        key=Config.WEBHOOK_SECRET.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()


def verify_signature(payload: bytes, signature: str) -> bool:
    """
    Vergelijk de ontvangen signature met de berekende HMAC.
    Gebruikt hmac.compare_digest om timing-attacks te voorkomen.
    """
    expected = compute_hmac(payload)
    ok = hmac.compare_digest(expected, signature)
    if not ok:
        logger.warning("HMAC verificatie mislukt – mogelijke ongeautoriseerde request")
    return ok
