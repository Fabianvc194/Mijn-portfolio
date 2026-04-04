import time
import pandas as pd
import ta
from datetime import datetime
from python_bitvavo_api.bitvavo import Bitvavo

# ---- Vul hier je Bitvavo API-gegevens in ----
API_KEY = ''
API_SECRET = ''
MARKET = 'ETH-EUR'
ORDER_SIZE = 0.01  # Gewenst aantal ETH per order
TIMEFRAME = '1h'   # '1h' voor 1 uur candles
SLEEP_TIME = 60    # Seconden tussen checks
MIN_ETH = 0.0018
MIN_EURO = 5.0
OPERATOR_ID = 12345  # Verplicht voor Bitvavo API

bitvavo = Bitvavo({'APIKEY': API_KEY, 'APISECRET': API_SECRET})

def tsprint(*args, **kwargs):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ", *args, **kwargs)

def get_ohlc(market=MARKET, interval=TIMEFRAME, limit=100):
    candles = bitvavo.candles(market, interval, {'limit': limit})
    df = pd.DataFrame(candles, columns=['timestamp','open','high','low','close','volume'])
    df[['open','high','low','close','volume']] = df[['open','high','low','close','volume']].astype(float)
    return df

def calculate_signals(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    macd = ta.trend.MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    # Koop bij: RSI < 30 & MACD > signaal --> bullish
    # Verkoop bij: RSI > 70 & MACD < signaal --> bearish
    if df['rsi'].iloc[-1] < 30 and df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]:
        return 'buy'
    elif df['rsi'].iloc[-1] > 70 and df['macd'].iloc[-1] < df['macd_signal'].iloc[-1]:
        return 'sell'
    else:
        return None

def calculate_min_amount(price):
    min_amount = max(MIN_ETH, round(MIN_EURO / price + 1e-8, 6))
    return max(min_amount, ORDER_SIZE)

def has_sufficient_balance(amount, asset):
    balanceinfo = bitvavo.balance({'symbol': asset})
    avail = float(balanceinfo[0]['available']) if balanceinfo else 0.0
    return avail >= amount

def place_limit_order(side, price, amount):
    # Zorg voor geldige minimale hoeveelheid
    min_amount = calculate_min_amount(price)
    actual_amount = max(amount, min_amount)
    price = round(price, 2)
    # Controleer balans
    asset = 'ETH' if side == 'sell' else 'EUR'
    if not has_sufficient_balance(actual_amount if side=='sell' else actual_amount*price, asset):
        tsprint(f"Onvoldoende saldo ({asset}) om {side} order te plaatsen.")
        return
    try:
        order = bitvavo.placeOrder(
            MARKET,
            side,
            'limit',
            {
                'amount': str(actual_amount),
                'price': str(price),
                'operatorId': OPERATOR_ID
            }
        )
        tsprint(f'Order {side} geplaatst: {order}')
    except Exception as e:
        tsprint(f"Order plaatsen mislukt: {e}")

while True:
    try:
        df = get_ohlc(limit=100)
        if df is None or len(df) < 30:
            tsprint("Niet genoeg data voor analyse.")
            time.sleep(SLEEP_TIME)
            continue
        sig = calculate_signals(df)
        last_close = df['close'].iloc[-1]
        tsprint(f"\n---\nLaatste prijs: {last_close:.2f} | Signaal: {sig}")
        if sig == 'buy':
            buy_px = round(last_close * 0.995, 2)
            place_limit_order('buy', buy_px, ORDER_SIZE)
        elif sig == 'sell':
            sell_px = round(last_close * 1.005, 2)
            place_limit_order('sell', sell_px, ORDER_SIZE)
        else:
            tsprint("Geen koop- of verkoop signaal.")
    except Exception as e:
        tsprint("Fout opgetreden:", e)
    time.sleep(SLEEP_TIME)
