#!/usr/bin/env python3
"""
sign_payload.py – Genereer HMAC-signatures voor alle drie de
authenticatie-methoden.

Gebruik:

  1) Header-signature (voor curl-tests):
     python sign_payload.py header '{"market":"BTC-EUR","action":"buy"}'

  2) Body-signature (voor TradingView alerts):
     python sign_payload.py body '{"market":"BTC-EUR","action":"buy"}'
     → print de volledige payload MET signature-veld, klaar om in
       TradingView te plakken.

  3) Toon je URL-token:
     python sign_payload.py token

Curl test-voorbeeld (methode 1 – header):
    PAYLOAD='{"market":"BTC-EUR","action":"buy"}'
    SIG=$(python sign_payload.py header "$PAYLOAD")
    curl -X POST http://localhost:5000/webhook \
         -H "Content-Type: application/json" \
         -H "X-Signature: $SIG" \
         -d "$PAYLOAD"

Curl test-voorbeeld (methode 3 – URL token):
    PAYLOAD='{"market":"BTC-EUR","action":"buy"}'
    TOKEN=$(python sign_payload.py token)
    curl -X POST "http://localhost:5000/webhook?token=$TOKEN" \
         -H "Content-Type: application/json" \
         -d "$PAYLOAD"
"""

import json
import sys

from config import Config
from security import compute_hmac


def header_signature(payload_str: str) -> None:
    """Bereken HMAC over de raw payload (methode 1)."""
    sig = compute_hmac(payload_str.encode("utf-8"))
    print(sig)


def body_signature(payload_str: str) -> None:
    """
    Bereken HMAC over de canonical payload (methode 2).
    Print de volledige JSON inclusief signature-veld.
    Plak dit direct in TradingView's alert message.
    """
    data = json.loads(payload_str)
    # Verwijder een eventuele bestaande signature
    data.pop("signature", None)
    # Canonical form: gesorteerde keys, geen spaties
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    sig = compute_hmac(canonical.encode("utf-8"))
    # Voeg signature toe en print leesbare JSON
    data["signature"] = sig
    print(json.dumps(data, indent=2))


def show_token() -> None:
    """Toon de WEBHOOK_SECRET voor URL-token methode (methode 3)."""
    print(Config.WEBHOOK_SECRET)


def main() -> None:
    usage = (
        "Gebruik:\n"
        "  python sign_payload.py header '<json>'\n"
        "  python sign_payload.py body   '<json>'\n"
        "  python sign_payload.py token\n"
    )

    if len(sys.argv) < 2:
        print(usage)
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "token":
        show_token()
    elif mode in ("header", "body") and len(sys.argv) >= 3:
        payload_str = sys.argv[2]
        if mode == "header":
            header_signature(payload_str)
        else:
            body_signature(payload_str)
    else:
        print(usage)
        sys.exit(1)


if __name__ == "__main__":
    main()
