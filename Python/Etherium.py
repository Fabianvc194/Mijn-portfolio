import numpy as np
import pandas as pd
import time
from datetime import datetime
from python_bitvavo_api.bitvavo import Bitvavo

# Bitvavo API setup
bitvavo = Bitvavo({
    'APIKEY': '',       # Vervang door eigen gegevens
    'APISECRET': ''
})

# Hulpfunctie voor nette logging met tijd/datum
def tsprint(*args, **kwargs):
    """Print alle logregels met datum en tijd voor overzichtelijke logging."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ", *args, **kwargs)

# Instellingen voor strategie en Bitvavo koppeling
KEY_VALUE = 1                  # Sensitiviteit van UT Bot Alerts; hoger maakt signaal minder gevoelig
ATR_PERIOD = 10                # Periode voor de ATR-berekening (volatiliteit)
AMOUNT = 0.01                  # Hoeveelheid ETH/EUR per trade (pas aan naar wens)
MARKET = 'ETH-EUR'             # Valutapaar gewijzigd naar Ethereum
TIMEFRAME = '15m'              # Tijdframe aangepast naar 15 minuten voor actieve trading
CHECK_INTERVAL = 60            # Hoe vaak script checkt op nieuwe signalen (in seconden)

# Functie om recente marktdata op te halen van Bitvavo
def get_data(limit=150):
    """
    Haalt de laatste candles op (open, high, low, close, volume) van Bitvavo.
    Zet deze data om naar een pandas DataFrame voor eenvoudige verwerking.
    """
    candles = bitvavo.candles(MARKET, TIMEFRAME, {'limit': limit})
    df = pd.DataFrame(candles, columns=['timestamp','open','high','low','close','volume'])
    for col in ['open','high','low','close','volume']:
        df[col] = df[col].astype(float)
    return df

# Bereken de ATR (Average True Range), een maat voor volatiliteit
def calculate_atr(df, period):
    """
    Berekening van ATR, veelgebruikt als maat voor marktvolatiliteit.
    Wordt gebruikt in UT Bot Alerts om trailing stops te bepalen.
    """
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def ut_bot_signal(df, key_value=1, atr_period=10):
    """
    De kern van de UT Bot Alerts-strategie:
    - Toepassing van trailing stops op basis van ATR en sensitiviteit (key_value).
    - Signaalberekening: 'buy' als trend omhoog draait, 'sell' als trend omlaag draait.
    Tegenovergesteld aan het Pine Script op TradingView, maar nu in Python uitgevoerd.
    """
    src = df['close']
    atr = calculate_atr(df, atr_period)
    nLoss = key_value * atr
    trailing_stop = [0.0] * len(src)
    pos = [0] * len(src)
    buy = [0] * len(src)
    sell = [0] * len(src)
    for i in range(1, len(df)):
        prev_ts = trailing_stop[i - 1]
        if src[i] > prev_ts and src[i - 1] > prev_ts:
            trailing_stop[i] = max(prev_ts, src[i] - nLoss.iloc[i])
        elif src[i] < prev_ts and src[i-1] < prev_ts:
            trailing_stop[i] = min(prev_ts, src[i] + nLoss.iloc[i])
        else:
            trailing_stop[i] = src[i] - nLoss.iloc[i] if src[i] > prev_ts else src[i] + nLoss.iloc[i]
        if src[i-1] < trailing_stop[i-1] and src[i] > trailing_stop[i]:
            pos[i] = 1
            buy[i] = 1
        elif src[i-1] > trailing_stop[i-1] and src[i] < trailing_stop[i]:
            pos[i] = -1
            sell[i] = 1
        else:
            pos[i] = pos[i-1]
    df['buy'] = buy
    df['sell'] = sell
    return df

def place_limit_order(side, price, amount=0.01):
    """
    Indient een limit order op Bitvavo voor het gekozen valutapaar.
    - 'side' bepaalt of het om een koop ('buy') of verkoop ('sell') gaat.
    - 'price' is de prijs waarop je wilt kopen/verkopen (gebaseerd op slotkoers candle).
    - 'amount' is het aantal coins dat gekocht/verkopen wordt.
    Logt meteen de order met tijd/datum.
    """
    price = round(price, 2)
    order = bitvavo.placeOrder({
        'market': MARKET,
        'side': side,
        'orderType': 'limit',
        'amount': str(amount),
        'price': str(price)
    })
    tsprint(f'Limit order {side} op prijs {price}: {order}')

# Hoofdloop - draait continu
laatste_trade_time = None     # Houdt candle-tijd bij van laatste order
laatste_trade_side = None     # Onthoudt het type laatste order: 'buy' of 'sell'

while True:
    try:
        df = get_data()
        df = ut_bot_signal(df, key_value=KEY_VALUE, atr_period=ATR_PERIOD)
        laatsteklus = df['close'].iloc[-1]
        timestamp = df['timestamp'].iloc[-1]
        # Bij een nieuw koop- of verkoopsignaal wordt een order geplaatst
        if df['buy'].iloc[-1]:
            if (laatste_trade_time != timestamp) or (laatste_trade_side != 'buy'):
                place_limit_order('buy', laatsteklus, amount=AMOUNT)
                laatste_trade_time = timestamp
                laatste_trade_side = 'buy'
            else:
                tsprint("Buy-signaal gedetecteerd, maar order voor deze candle reeds geplaatst.")
        elif df['sell'].iloc[-1]:
            if (laatste_trade_time != timestamp) or (laatste_trade_side != 'sell'):
                place_limit_order('sell', laatsteklus, amount=AMOUNT)
                laatste_trade_time = timestamp
                laatste_trade_side = 'sell'
            else:
                tsprint("Sell-signaal gedetecteerd, maar order voor deze candle reeds geplaatst.")
        else:
            tsprint("Geen nieuw trade-signaal gedetecteerd.")
    except Exception as e:
        tsprint("Fout opgetreden:", e)
    time.sleep(CHECK_INTERVAL)
