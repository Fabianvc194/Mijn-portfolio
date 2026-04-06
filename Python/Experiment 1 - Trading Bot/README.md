# Bitvavo Trading Bot - Conservative Trend-Following Strategy

Deze professionele trading bot is ontworpen voor Bitvavo exchange, specifiek voor BTC/EUR en ETH/EUR paren. De bot gebruikt een conservatieve trend-following strategie met risicomanagement.

## Strategie Overzicht

### Trendbepaling (1h timeframe)
- 200-period EMA: Handel alleen 'long' als de huidige prijs boven de EMA ligt (positieve lange-termijn trend).

### Entry Signal (15m timeframe)
- Bollinger Bands (20, 2): Koop wanneer de prijs de onderste band raakt.
- RSI (14): Moet onder de 40 zijn voor bevestiging (mean reversion in uptrend).

### Risicomanagement
- **Position Sizing**: Maximaal 10% van beschikbaar EUR saldo per trade.
- **Trailing Stop-Loss**: 1.5% trailing stop, geactiveerd na 1% winst.
- **Slippage Protection**: Gebruikt limit orders in plaats van market orders.
- **Cooldown**: 4 uur cooldown na elke gesloten trade voor hetzelfde paar.

## Installatie

1. Installeer dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configureer API keys in `config.py`:
   - Verkrijg API key en secret van je Bitvavo account.
   - Plaats deze in de `API_KEY` en `API_SECRET` variabelen.

3. Start de bot:
   ```bash
   python trading_bot.py
   ```

## Configuratie

Alle instellingen staan in `config.py`:
- API credentials
- Trading paren en timeframes
- Indicator parameters
- Risico instellingen
- Logging configuratie

## Logging

Alle trades worden gelogd in `trading_log.csv` met:
- Timestamp
- Symbol
- Action (entry/exit)
- Prijs
- Amount
- Reden
- P&L (na aftrek van 0.25% Bitvavo fees)

## Belangrijke Opmerkingen

- **Test eerst**: Gebruik paper trading of kleine amounts om de bot te testen.
- **API Limits**: Bitvavo heeft rate limits; de bot respecteert deze via CCXT.
- **Risico**: Cryptocurrency trading is risicovol. Gebruik alleen geld dat je kunt missen.
- **Monitoring**: Houd de bot in de gaten en stop indien nodig.

## Code Structuur

- `config.py`: Configuratie en instellingen
- `trading_bot.py`: Hoofdklasse TradingBot met alle logica
- `requirements.txt`: Python dependencies
- `trading_log.csv`: Trade logging (wordt aangemaakt bij eerste trade)

De bot gebruikt asyncio voor gelijktijdige monitoring van beide paren en implementeert professionele trading praktijken.