# config.py - Configuratie voor Bitvavo Trading Bot
# Plaats je eigen API-sleutels hier (verkrijg deze van Bitvavo dashboard)
API_KEY = 'your_api_key_here'
API_SECRET = 'your_api_secret_here'

# Trading instellingen
SYMBOLS = ['BTC/EUR', 'ETH/EUR']  # Te monitoren valutaparen
TIMEFRAME_TREND = '1h'  # Voor trendbepaling (EMA 200)
TIMEFRAME_ENTRY = '15m'  # Voor entry signalen (Bollinger Bands, RSI)
EMA_PERIOD = 200  # Periode voor EMA op 1h chart
BB_PERIOD = 20  # Periode voor Bollinger Bands op 15m chart
BB_STD = 2  # Standaardafwijking voor Bollinger Bands
RSI_PERIOD = 14  # Periode voor RSI berekening
RSI_OVERBOUGHT = 70  # Niet gebruikt in deze strategie, maar voor volledigheid
RSI_OVERSOLD = 40  # Drempel voor koop signaal

# Risicomanagement
MAX_POSITION_SIZE_PCT = 0.10  # Maximaal 10% van EUR saldo per trade
TRAILING_STOP_PCT = 0.015  # 1.5% trailing stop
PROFIT_ACTIVATION_PCT = 0.01  # Activeer trailing stop na 1% winst
COOLDOWN_HOURS = 4  # Cooldown periode na trade (in uren)

# Order instellingen
ORDER_TYPE = 'limit'  # Gebruik limit orders voor slippage protection
SLIPPAGE_PCT = 0.001  # 0.1% slippage voor limit order prijsberekening

# Logging
LOG_FILE = 'trading_log.csv'  # CSV bestand voor trade logging
BITVAVO_FEE_PCT = 0.0025  # 0.25% fee per trade

# Andere instellingen
CHECK_INTERVAL = 60  # Controleer elke 60 seconden op nieuwe signalen
DATA_LIMIT = 500  # Aantal candles om op te halen voor berekeningen