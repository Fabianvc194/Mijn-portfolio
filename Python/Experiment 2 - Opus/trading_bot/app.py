"""
app.py – Flask webhook server.

Endpoints:
  POST /webhook   – ontvang TradingView alerts (multi-auth)
  GET  /health    – liveness check

Authenticatie (drie methoden, in volgorde van prioriteit):
  1. X-Signature header   – HMAC-SHA256 over de raw body
  2. "signature" veld     – HMAC-SHA256 in de JSON payload zelf
  3. ?token= query param  – directe vergelijking met WEBHOOK_SECRET

Methode 1 is het veiligst, maar TradingView ondersteunt geen
custom headers. Methode 2 en 3 zijn workarounds voor TV.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

from flask import Flask, Response, jsonify, request

from config import Config
from exchange import Exchange
from security import verify_signature, compute_hmac
from trading import Signal, TradingEngine

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Applicatie-setup
# ------------------------------------------------------------------
app = Flask(__name__)
exchange = Exchange()
engine = TradingEngine(exchange)


# ------------------------------------------------------------------
# Authenticatie helpers
# ------------------------------------------------------------------

def _authenticate(raw_body: bytes) -> tuple[bool, str]:
    """
    Probeer de request te authenticeren via drie methoden.

    Returns:
        (is_authenticated, methode_naam)
    """

    # ── Methode 1: X-Signature header (ideaal) ──────────────────
    header_sig = request.headers.get("X-Signature", "")
    if header_sig:
        if verify_signature(raw_body, header_sig):
            return True, "header"
        logger.warning("X-Signature header aanwezig maar ongeldig")
        return False, "header"

    # ── Methode 2: signature veld in JSON body ───────────────────
    #
    # TradingView stuurt:
    #   {"market":"BTC-EUR","action":"buy","signature":"<hmac>"}
    #
    # De HMAC wordt berekend over de payload ZONDER het signature-
    # veld, zodat de signature zichzelf niet beïnvloedt.
    try:
        body_json = json.loads(raw_body)
    except (json.JSONDecodeError, ValueError):
        body_json = {}

    body_sig = body_json.get("signature", "")
    if body_sig:
        payload_without_sig = {
            k: v for k, v in body_json.items() if k != "signature"
        }
        canonical = json.dumps(
            payload_without_sig, sort_keys=True, separators=(",", ":")
        )
        expected = compute_hmac(canonical.encode("utf-8"))
        if hmac.compare_digest(expected, body_sig):
            return True, "body"
        logger.warning("Body-signature aanwezig maar ongeldig")
        return False, "body"

    # ── Methode 3: URL token (?token=...) ────────────────────────
    #
    # Webhook URL: https://jouw-domein.nl/webhook?token=<secret>
    url_token = request.args.get("token", "")
    if url_token:
        if hmac.compare_digest(url_token, Config.WEBHOOK_SECRET):
            return True, "token"
        logger.warning("URL token aanwezig maar ongeldig")
        return False, "token"

    # Geen enkele authenticatie gevonden
    return False, "none"


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health() -> Response:
    return jsonify({"status": "ok", "ts": datetime.now(timezone.utc).isoformat()})


@app.route("/webhook", methods=["POST"])
def webhook() -> tuple[Response, int]:
    """
    Ontvang een TradingView webhook alert.

    Authenticatie: zie module-docstring voor de drie methoden.

    Verwacht JSON body:
        {
            "market":    "BTC-EUR",
            "action":    "buy",
            "risk_pct":  2.0,          // optioneel
            "signature": "abc123..."   // optioneel (methode 2)
        }
    """
    raw_body = request.get_data()

    # ── Authenticatie ──
    is_auth, method = _authenticate(raw_body)
    if not is_auth:
        if method == "none":
            logger.warning("Webhook zonder enige authenticatie ontvangen")
            return jsonify({"error": "No authentication provided"}), 401
        return jsonify({"error": f"Invalid {method} authentication"}), 403

    logger.info("Webhook geauthenticeerd via: %s", method)

    # ── Payload parsen ──
    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON"}), 400

    market = data.get("market", "").upper()
    action = data.get("action", "").lower()

    if not market or action not in ("buy", "sell"):
        return jsonify({"error": "Missing or invalid 'market' / 'action'"}), 400

    # ── Uitvoeren ──
    signal = Signal(
        market=market,
        action=action,
        risk_pct=data.get("risk_pct"),
    )
    logger.info("Signal ontvangen: %s %s", signal.action, signal.market)

    try:
        result = engine.execute(signal)
    except Exception:
        logger.exception("Onverwachte fout bij uitvoering")
        return jsonify({"error": "Internal execution error"}), 500

    return jsonify(result), 200


# ------------------------------------------------------------------
# Entrypoint (development)
# ------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
