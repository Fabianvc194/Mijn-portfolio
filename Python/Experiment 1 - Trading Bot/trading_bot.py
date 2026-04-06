# trading_bot.py - Professionele Bitvavo Trading Bot via CCXT
import asyncio
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import csv
import os
from config import *

class TradingBot:
    def __init__(self, symbol):
        self.symbol = symbol
        self.exchange = ccxt.bitvavo({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'enableRateLimit': True,
        })
        self.position = None  # {'side': 'long', 'entry_price': float, 'amount': float, 'highest_price': float, 'trailing_stop': float}
        self.last_trade_time = None
        self.cooldown_until = None

    async def get_ohlcv(self, timeframe, limit=DATA_LIMIT):
        """Haal OHLCV data op voor gegeven timeframe."""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df
        except Exception as e:
            print(f"Fout bij ophalen data voor {self.symbol}: {e}")
            return None

    def calculate_ema(self, df, period):
        """Bereken Exponential Moving Average."""
        return df['close'].ewm(span=period, adjust=False).mean()

    def calculate_bollinger_bands(self, df, period, std_dev):
        """Bereken Bollinger Bands."""
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return sma, upper, lower

    def calculate_rsi(self, df, period):
        """Bereken Relative Strength Index."""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    async def get_balance(self):
        """Haal EUR saldo op."""
        try:
            balance = await self.exchange.fetch_balance()
            return balance['EUR']['free']
        except Exception as e:
            print(f"Fout bij ophalen saldo: {e}")
            return 0

    async def check_trend(self):
        """Controleer lange-termijn trend met 200 EMA op 1h."""
        df_1h = await self.get_ohlcv(TIMEFRAME_TREND, limit=EMA_PERIOD + 50)
        if df_1h is None or len(df_1h) < EMA_PERIOD:
            return False
        ema_200 = self.calculate_ema(df_1h, EMA_PERIOD)
        current_price = df_1h['close'].iloc[-1]
        return current_price > ema_200.iloc[-1]

    async def check_entry_signal(self):
        """Controleer entry signaal met Bollinger Bands en RSI op 15m."""
        df_15m = await self.get_ohlcv(TIMEFRAME_ENTRY, limit=BB_PERIOD + RSI_PERIOD + 50)
        if df_15m is None or len(df_15m) < max(BB_PERIOD, RSI_PERIOD):
            return False
        sma, upper, lower = self.calculate_bollinger_bands(df_15m, BB_PERIOD, BB_STD)
        rsi = self.calculate_rsi(df_15m, RSI_PERIOD)
        current_price = df_15m['close'].iloc[-1]
        prev_price = df_15m['close'].iloc[-2]
        # Koop als prijs onderste band raakt (van bovenaf) EN RSI < 40
        return (prev_price > lower.iloc[-2] and current_price <= lower.iloc[-1]) and (rsi.iloc[-1] < RSI_OVERSOLD)

    async def calculate_position_size(self):
        """Bereken position size: max 10% van EUR saldo."""
        eur_balance = await self.get_balance()
        position_value = eur_balance * MAX_POSITION_SIZE_PCT
        current_price = (await self.get_ohlcv(TIMEFRAME_ENTRY, limit=1))['close'].iloc[-1]
        amount = position_value / current_price
        return amount, current_price

    async def place_limit_order(self, side, amount, price):
        """Plaats limit order met slippage protection."""
        try:
            order = await self.exchange.create_order(
                self.symbol,
                ORDER_TYPE,
                side,
                amount,
                price
            )
            print(f"Order geplaatst: {side} {amount} {self.symbol} @ {price}")
            return order
        except Exception as e:
            print(f"Fout bij plaatsen order: {e}")
            return None

    async def open_position(self, side='buy'):
        """Open nieuwe positie."""
        if self.position is not None:
            return
        amount, entry_price = await self.calculate_position_size()
        # Bereken limit prijs met kleine slippage
        slippage_price = entry_price * (1 + SLIPPAGE_PCT) if side == 'buy' else entry_price * (1 - SLIPPAGE_PCT)
        order = await self.place_limit_order(side, amount, slippage_price)
        if order:
            self.position = {
                'side': 'long',
                'entry_price': entry_price,
                'amount': amount,
                'highest_price': entry_price,
                'trailing_stop': entry_price * (1 - TRAILING_STOP_PCT),
                'order_id': order['id']
            }
            self.last_trade_time = datetime.now()
            self.cooldown_until = self.last_trade_time + timedelta(hours=COOLDOWN_HOURS)
            self.log_trade('entry', entry_price, amount, 'Trend-following entry signal')

    async def close_position(self, exit_price, reason):
        """Sluit positie."""
        if self.position is None:
            return
        side = 'sell' if self.position['side'] == 'long' else 'buy'
        slippage_price = exit_price * (1 - SLIPPAGE_PCT) if side == 'sell' else exit_price * (1 + SLIPPAGE_PCT)
        order = await self.place_limit_order(side, self.position['amount'], slippage_price)
        if order:
            pnl = (exit_price - self.position['entry_price']) * self.position['amount'] if self.position['side'] == 'long' else (self.position['entry_price'] - exit_price) * self.position['amount']
            fee = abs(pnl) * BITVAVO_FEE_PCT * 2  # Fee voor entry en exit
            net_pnl = pnl - fee
            self.log_trade('exit', exit_price, self.position['amount'], reason, net_pnl)
            self.position = None
            self.last_trade_time = datetime.now()
            self.cooldown_until = self.last_trade_time + timedelta(hours=COOLDOWN_HOURS)

    async def update_trailing_stop(self, current_price):
        """Update trailing stop als positie in winst is."""
        if self.position is None:
            return
        if current_price > self.position['highest_price']:
            self.position['highest_price'] = current_price
            if (current_price - self.position['entry_price']) / self.position['entry_price'] >= PROFIT_ACTIVATION_PCT:
                self.position['trailing_stop'] = self.position['highest_price'] * (1 - TRAILING_STOP_PCT)

    async def check_stop_loss(self, current_price):
        """Controleer of trailing stop is geraakt."""
        if self.position and current_price <= self.position['trailing_stop']:
            await self.close_position(current_price, 'Trailing stop hit')

    def log_trade(self, action, price, amount, reason, pnl=None):
        """Log trade naar CSV."""
        file_exists = os.path.isfile(LOG_FILE)
        with open(LOG_FILE, 'a', newline='') as csvfile:
            fieldnames = ['timestamp', 'symbol', 'action', 'price', 'amount', 'reason', 'pnl']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                'timestamp': datetime.now().isoformat(),
                'symbol': self.symbol,
                'action': action,
                'price': price,
                'amount': amount,
                'reason': reason,
                'pnl': pnl if pnl is not None else ''
            })

    async def monitor(self):
        """Monitor functie voor één symbol."""
        while True:
            try:
                now = datetime.now()
                if self.cooldown_until and now < self.cooldown_until:
                    await asyncio.sleep(CHECK_INTERVAL)
                    continue

                current_price = (await self.get_ohlcv(TIMEFRAME_ENTRY, limit=1))['close'].iloc[-1]

                if self.position:
                    await self.update_trailing_stop(current_price)
                    await self.check_stop_loss(current_price)
                else:
                    trend_up = await self.check_trend()
                    entry_signal = await self.check_entry_signal()
                    if trend_up and entry_signal:
                        await self.open_position()

                await asyncio.sleep(CHECK_INTERVAL)
            except Exception as e:
                print(f"Fout in monitor loop voor {self.symbol}: {e}")
                await asyncio.sleep(CHECK_INTERVAL)

async def main():
    """Hoofdloop: start monitoring voor beide symbolen."""
    bots = {symbol: TradingBot(symbol) for symbol in SYMBOLS}
    tasks = [bot.monitor() for bot in bots.values()]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())