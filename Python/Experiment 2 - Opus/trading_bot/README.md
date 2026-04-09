# Trading Bot – Deployment Handleiding

## Architectuuroverzicht

```
TradingView Alert
       │
       ▼
 ┌─────────────┐   HMAC-SHA256    ┌──────────────┐
 │  Flask App   │◄── verificatie ──│  security.py │
 │  (app.py)    │                  └──────────────┘
 └──────┬───────┘
        │ Signal
        ▼
 ┌──────────────┐   position size   ┌────────────┐
 │ TradingEngine│◄── berekening ────│  risk.py   │
 │ (trading.py) │                   └────────────┘
 └──────┬───────┘
        │ orders
        ▼
 ┌──────────────┐                   ┌────────────┐
 │  Exchange    │◄── credentials ───│ config.py  │
 │(exchange.py) │                   └────────────┘
 └──────┬───────┘
        │ REST API
        ▼
    Bitvavo.com
```

---

## 1. Vereisten

- Python 3.11+
- Een Bitvavo-account met API-keys (met "Trade" permissie)
- Een VPS met een publiek IP-adres (DigitalOcean, Hetzner, etc.)
- Een TradingView-account (gratis werkt, Pro+ voor meer alerts)

---

## 2. Installatie op VPS

```bash
# Verbind met je VPS
ssh root@jouw-vps-ip

# Maak een dedicated user aan
adduser tradingbot
usermod -aG sudo tradingbot
su - tradingbot

# Installeer Python + venv
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nginx

# Clone of upload de bestanden
mkdir ~/trading_bot && cd ~/trading_bot
# (kopieer alle .py bestanden + requirements.txt hierheen)

# Virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 3. Configuratie

```bash
# Kopieer het template en vul je eigen waarden in
cp .env.example .env
nano .env
```

Genereer een sterk webhook-geheim:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Plak het resultaat als `WEBHOOK_SECRET` in `.env`.

---

## 4. Testen (lokaal)

```bash
source venv/bin/activate

# Start de server
python app.py

# In een tweede terminal: genereer een signature en test
PAYLOAD='{"market":"BTC-EUR","action":"buy"}'
SIG=$(python sign_payload.py "$PAYLOAD")
curl -X POST http://localhost:5000/webhook \
     -H "Content-Type: application/json" \
     -H "X-Signature: $SIG" \
     -d "$PAYLOAD"
```

---

## 5. Production Deployment met systemd + Gunicorn

### 5a. Systemd service

```bash
sudo nano /etc/systemd/system/tradingbot.service
```

Inhoud:

```ini
[Unit]
Description=Trading Bot Webhook Server
After=network.target

[Service]
User=tradingbot
WorkingDirectory=/home/tradingbot/trading_bot
ExecStart=/home/tradingbot/trading_bot/venv/bin/gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 1 \
    --timeout 30 \
    app:app
Restart=always
RestartSec=5
EnvironmentFile=/home/tradingbot/trading_bot/.env

[Install]
WantedBy=multi-user.target
```

**Let op:** gebruik `--workers 1` omdat de trailing stop threads
in-process draaien. Meerdere workers zouden duplicaat-stops creëren.

```bash
sudo systemctl daemon-reload
sudo systemctl enable tradingbot
sudo systemctl start tradingbot
sudo systemctl status tradingbot
```

### 5b. Nginx reverse proxy + HTTPS

```bash
sudo nano /etc/nginx/sites-available/tradingbot
```

```nginx
server {
    listen 80;
    server_name jouw-domein.nl;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Signature $http_x_signature;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/tradingbot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# HTTPS via Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d jouw-domein.nl
```

---

## 6. TradingView Alert Configuratie

TradingView ondersteunt geen custom HTTP-headers. Daarom biedt
de bot drie authenticatie-methoden. Kies er één.

---

### Methode A – URL Token (snelste setup)

**Webhook URL in TradingView:**
```
https://jouw-domein.nl/webhook?token=JOUW_WEBHOOK_SECRET
```

**Alert Message (plak dit in het "Message" veld):**
```json
{"market":"BTC-EUR","action":"buy","risk_pct":2.0}
```

Haal je token op met:
```bash
python sign_payload.py token
```

> ⚠️ Het token staat in de URL en is zichtbaar in server-logs.
> Gebruik HTTPS zodat het niet over het netwerk lekt.

---

### Methode B – HMAC in de JSON Body (aanbevolen)

**Webhook URL:**
```
https://jouw-domein.nl/webhook
```

Genereer eerst de payload met signature:
```bash
python sign_payload.py body '{"market":"BTC-EUR","action":"buy","risk_pct":2.0}'
```

Output (voorbeeld):
```json
{
  "market": "BTC-EUR",
  "action": "buy",
  "risk_pct": 2.0,
  "signature": "a1b2c3d4e5f6..."
}
```

**Plak deze volledige output in het TradingView "Message" veld.**

De bot berekent de HMAC over alle velden BEHALVE `signature`,
en vergelijkt het resultaat. Dit is veiliger dan de URL-token
methode omdat het geheim niet in logs verschijnt.

> ⚠️ De signature is statisch: bij elke unieke payload-combinatie
> (ander market, action, risk_pct) moet je een nieuwe genereren.

**Veelgebruikte payloads (genereer ze allemaal vooraf):**

```bash
# BTC kopen
python sign_payload.py body '{"market":"BTC-EUR","action":"buy","risk_pct":2.0}'

# BTC verkopen
python sign_payload.py body '{"market":"BTC-EUR","action":"sell"}'

# ETH kopen
python sign_payload.py body '{"market":"ETH-EUR","action":"buy","risk_pct":2.0}'

# ETH verkopen
python sign_payload.py body '{"market":"ETH-EUR","action":"sell"}'
```

---

### Methode C – X-Signature Header (voor eigen systemen)

Als je een eigen systeem hebt dat custom headers kan sturen
(bijv. een Cloudflare Worker, n8n, of eigen script):

**Webhook URL:**
```
https://jouw-domein.nl/webhook
```

**Header:**
```
X-Signature: <hmac-sha256 hex digest van de raw body>
```

Genereer de signature:
```bash
python sign_payload.py header '{"market":"BTC-EUR","action":"buy"}'
```

Test met curl:
```bash
PAYLOAD='{"market":"BTC-EUR","action":"buy"}'
SIG=$(python sign_payload.py header "$PAYLOAD")
curl -X POST https://jouw-domein.nl/webhook \
     -H "Content-Type: application/json" \
     -H "X-Signature: $SIG" \
     -d "$PAYLOAD"
```

---

## 7. Bestandsstructuur

```
trading_bot/
├── .env.example      # Template voor environment variables
├── .env              # Jouw lokale configuratie (NIET committen)
├── requirements.txt  # Python dependencies
├── config.py         # Gecentraliseerde configuratie
├── security.py       # HMAC-SHA256 webhook verificatie
├── exchange.py       # Bitvavo API wrapper
├── risk.py           # Position sizing + trailing stop-loss
├── trading.py        # Trading engine (signaalverwerking)
├── app.py            # Flask server (entrypoint)
└── sign_payload.py   # Hulpscript voor HMAC-generatie
```

---

## 8. Logging & Monitoring

Bekijk live logs:

```bash
sudo journalctl -u tradingbot -f
```

Alle logs worden naar stdout geschreven in het formaat:
```
2026-01-15 14:30:22 [INFO] trading – Signal ontvangen: buy BTC-EUR
2026-01-15 14:30:22 [INFO] trading – Placing buy BTC-EUR: 0.00042000 @ 83250.00 EUR
2026-01-15 14:30:23 [INFO] risk – Trailing stop gestart: BTC-EUR | entry=83250.00 | trail=3.0%
```

---

## 9. Veiligheidsaanbevelingen

1. **Firewall**: Sta alleen poort 80/443 toe (`sudo ufw allow 'Nginx Full'`)
2. **API permissies**: Geef je Bitvavo API-key alleen "Trade" rechten, geen "Withdraw"
3. **IP-whitelist**: Beperk de Bitvavo API-key tot het IP van je VPS
4. **.env beveiliging**: `chmod 600 .env` – alleen de service-user mag lezen
5. **Rate limits**: Bitvavo staat 1000 requests/minuut toe; de bot is hier ruim binnen

---

## 10. Belangrijk Disclaimer

Deze bot is een hulpmiddel, geen financieel advies. Crypto-trading
brengt aanzienlijke risico's met zich mee. Test altijd eerst met
kleine bedragen en monitor de bot actief. De auteur is niet
aansprakelijk voor eventuele verliezen.
