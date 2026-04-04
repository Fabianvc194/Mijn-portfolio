import numpy as np
import pandas as pd
import time


from python_bitvavo_api.bitvavo import Bitvavo

# Bitvavo API setup
bitvavo = Bitvavo({
    'APIKEY': '',       # Vervang door eigen gegevens
    'APISECRET': ''
})

KEY_VALUE = 1
ATR_PERIOD = 10
AMOUNT = 0.01                    # Pas zelf aan
MARKET = 'BTC-EUR'
TIMEFRAME = '1h'
CHECK_INTERVAL = 60             # Elke 900 sec = 15 minuten (pas aan naar gewenste frequentie)

def get_data(limit=150):
    candles = bitvavo.candles(MARKET, TIMEFRAME, {'limit': limit})
    df = pd.DataFrame(candles, columns=['timestamp','open','high','low','close','volume'])
    for col in ['open','high','low','close','volume']:
        df[col] = df[col].astype(float)
    return df

def calculate_atr(df, period):
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
    price = round(price, 2)
    order = bitvavo.placeOrder({
        'market': MARKET,
        'side': side,
        'orderType': 'limit',
        'amount': str(amount),
        'price': str(price)
    })
    print(f'Limit order {side} op {price}: {order}')

# Onthoudt orderstatus voor de laatste candle-timestamp om dubbele trades te voorkomen
laatste_trade_time = None
laatste_trade_side = None

while True:
    try:
        df = get_data()
        df = ut_bot_signal(df, key_value=KEY_VALUE, atr_period=ATR_PERIOD)

        laatsteklus = df['close'].iloc[-1]
        timestamp = df['timestamp'].iloc[-1]
        if df['buy'].iloc[-1]:
            if (laatste_trade_time != timestamp) or (laatste_trade_side != 'buy'):
                place_limit_order('buy', laatsteklus, amount=AMOUNT)
                laatste_trade_time = timestamp
                laatste_trade_side = 'buy'
            else:
                print("Buy-signaal, maar order voor deze candle is al geplaatst.")
        elif df['sell'].iloc[-1]:
            if (laatste_trade_time != timestamp) or (laatste_trade_side != 'sell'):
                place_limit_order('sell', laatsteklus, amount=AMOUNT)
                laatste_trade_time = timestamp
                laatste_trade_side = 'sell'
            else:
                print("Sell-signaal, maar order voor deze candle is al geplaatst.")
        else:
            print("Geen nieuw trade-signaal.")
    except Exception as e:
        print("Fout opgetreden:", e)
    time.sleep(CHECK_INTERVAL)
