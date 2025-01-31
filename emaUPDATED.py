from ta.momentum import RSIIndicator
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time

def RSI(df, n):
    rsi = RSIIndicator(df, n).rsi()
    return rsi

def EMA(df, n):
    ema = df.ewm(span=n, adjust = False).mean()
    return ema

def ATR(df, n):
    df['h-l'] = df['high'] - df['low']
    df['h-c'] = df['high'] - df['close'].shift().abs()
    df['l-c'] = df['low'] - df['close'].shift().abs()

    df['tr'] = df[['h-l','h-c','l-c']].max(axis=1)

    atr = EMA(df['tr'], n)

    return atr

def BB(df, n):
    prices = df['close']
    middle = prices.rolling(window = n).mean()
    std_dev = prices.rolling(window = n).std()
    upper = middle + (2 * std_dev)
    lower = middle - (2 * std_dev)
    distance = (upper - lower).abs()
    return lower, middle, upper, distance


def DATA(symbol, n=30):
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, n)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['ema_9'] = EMA(df['close'], 9)
    df['ema_21'] = EMA(df['close'], 21)
    df['ema_50'] = EMA(df['close'], 50)
    df['ema_150'] = EMA(df['close'], 150)

    df['RSI'] = RSI(df = df['close'], n = 7)
    return df

def SLTP(symbol, type, balance, df):
    info = mt5.symbol_info(symbol)
    price = mt5.symbol_info_tick(symbol)
    price = price.ask

    contract_size = info.trade_contract_size
    min_lot = info.volume_min
    lot_step =info.volume_step
    max_lot = info.volume_max

    tp_multiplier = 1.4
    risk = 0.1

    risk_amount = risk * balance

    atr = ATR(df, 14).iloc[-1]

    stop_loss_distance = info.trade_stops_level * info.point * 1.01
    take_profit_distance = atr * tp_multiplier


    lot_size_units = risk_amount / stop_loss_distance if stop_loss_distance > 0 else 0
    position_size_lots = lot_size_units / contract_size

    volume = max(min_lot, min(max_lot, round(position_size_lots / lot_step) * lot_step))

    atr = ATR(df, 14).iloc[-1]

    if type == mt5.ORDER_TYPE_BUY:
        sl = price - stop_loss_distance
        tp = price + take_profit_distance
    elif type == mt5.ORDER_TYPE_SELL:
        sl = price + stop_loss_distance
        tp = price - take_profit_distance
    else:
        return None
    
    return sl, tp, volume, price


def PURCHASE(symbol, type, tp, sl, volume, price):
    
    request = {
        'action':mt5.TRADE_ACTION_DEAL,
        'symbol':symbol,
        'volume':volume,
        'type':type,
        'price':price,
        'sl':sl,
        'tp':tp,
        'deviation':20,
        'magic': 12345678,
        'comment':'Python script open',
        'type_time':mt5.ORDER_TIME_GTC,
        'type_filling': mt5.ORDER_FILLING_IOC
    }

    result = mt5.order_send(request)
    return result


def S1(df, symbol, balance):
    sl, tp, volume, price = SLTP(symbol, type, balance, df)
    df = DATA(symbol)
    latest = df.iloc[-1]
    previous = df.iloc[-2]

    if previous['ema_9'] < previous['ema_21'] and latest['ema_9'] > latest['ema_21'] and latest['RSI'] < 70:
        print(symbol, 'BUY')
        res = PURCHASE(symbol = symbol,
                    type = mt5.ORDER_TYPE_BUY,
                    balance = balance,
                    df = df,
                    sl = sl,
                    tp = tp,
                    volume = volume,
                    price = price)
    elif previous['ema_9'] > previous['ema_21'] and latest['ema_9'] < latest['ema_21'] and latest['RSI'] > 30:
        print(symbol, 'SELL')
        res = PURCHASE(symbol = symbol,
                    type = mt5.ORDER_TYPE_SELL,
                    balance = balance,
                    df = df,
                    sl = sl,
                    tp = tp,
                    volume = volume,
                    price = price)


def S2(df, balance, symbol):
    sl, tp, volume, price = SLTP(symbol, type, balance, df)
    latest = df.iloc[-1]
    previous = df.iloc[-2]

    ema_20 = df['ema_21']
    ema_10 = df['ema_9']
    ema_5 = df['ema_5']
    rsi = df['RSI']

    if ema_10.iloc[-1] > ema_20.iloc[-2]:
        c1 = latest['close'] > latest['open']
        c2 = previous['open'] > previous['close']
        c3 = latest['close'] > previous['open']
        c4 = rsi.iloc[-1] > rsi.iloc[-2]
        c5 = latest['open'] <= ema_10.iloc[-1]
        c6 = latest['close'] < ema_5.iloc[-1]
        c7 = ema_20.iloc[-1] > ema_20.iloc[-2]
        if all([c1, c2, c3, c4, c5, c6, c7]):
            print(symbol, 'BUY')
            res = PURCHASE(symbol = symbol,
                        type = mt5.ORDER_TYPE_BUY,
                        balance = balance,
                        df = df,
                        sl = sl,
                        tp = tp,
                        volume = volume,
                        price = price)
       
    elif ema_10.iloc[-1] < ema_20.iloc[-2]:
        c1 = latest['close'] < latest['open']
        c2 = previous['open'] < previous['close']
        c3 = latest['close'] < previous['open']
        c4 = rsi.iloc[-1] < rsi.iloc[-2]
        c5 = latest['open'] >= ema_10.iloc[-1]
        c6 = latest['close'] > ema_5.iloc[-1]
        c7 = ema_20.iloc[-1] < ema_20.iloc[-2]
        if all([c1, c2, c3, c4, c5, c6, c7]):
            print(symbol, 'SELL')
            res = PURCHASE(symbol = symbol,
                        type = mt5.ORDER_TYPE_SELL,
                        balance = balance,
                        df = df,
                        sl = sl,
                        tp = tp,
                        volume = volume,
                        price = price)


def S3(df, balance, symbol):
    sl, tp, volume, price = SLTP(symbol, type, balance, df)
    ema_9 = df['ema_9']
    ema_5 = df['ema_5']

    if ema_5.iloc[-5] - ema_5.iloc[-3] > 0 and ema_5.iloc[-3] - ema_5.iloc[-1] < 0:
        print(symbol, 'BUY')
        res = PURCHASE(symbol = symbol,
                    type = mt5.ORDER_TYPE_BUY,
                    balance = balance,
                    df = df,
                    sl = sl,
                    tp = tp,
                    volume = volume,
                    price = price)
    elif ema_5.iloc[-5] - ema_5.iloc[-3] < 0 and ema_5.iloc[-3] - ema_5.iloc[-1] > 0:
        print(symbol, 'SELL')
        res = PURCHASE(symbol = symbol,
                       type = mt5.ORDER_TYPE_SELL,
                       balance = balance,
                       df = df,
                       sl = sl,
                        tp = tp,
                        volume = volume,
                        price = price)


def S4(df, symbol, balance):
    sl, tp, volume, price = SLTP(symbol, type, balance, df)
    latest = df.iloc[-1]

    if latest['ema_50'] > latest['ema_150']:
        c1 = latest['open'] < latest['close']
        c2 = latest['low'] < latest['ema_150']
        c3 = latest['low'] > max(df['high'].iloc[-10:-1])
        c4 = latest['RSI'] < 30
        if all([c1, c2, c3, c4]):

            print(symbol, 'BUY')
            res = PURCHASE(symbol = symbol,
                        type = mt5.ORDER_TYPE_BUY,
                        balance = balance,
                        df = df,
                        sl = sl,
                        tp = tp,
                        volume = volume,
                        price = price)

    elif latest['ema_50'] < latest['ema_150']:
        c1 = latest['close'] > latest['open']
        c2 = latest['high'] > latest['ema_150']
        c3 = latest['high'] < max(df['high'].iloc[-10:-1])
        c4 = latest['RSI'] > 70
        if all([c1, c2, c3, c4]):

            print(symbol, 'SELL')
            res = PURCHASE(symbol = symbol,
                        type = mt5.ORDER_TYPE_SELL,
                        balance = balance,
                        df = df,
                        sl = sl,
                        tp = tp,
                        volume = volume,
                        price = price)

def S5(df, symbol, balance):

    lower, middle, upper, distance = BB(df = df, n = 20)


    latest = df.iloc[-1]


    if latest['open'] < latest['close']:
        c1 = latest['close'] > upper.iloc[-1]
        c2 = latest['RSI'] < 50
        c3 = distance.iloc[-2] < distance.iloc[-1]
        if all([c1, c2, c3]):
            sl = middle.iloc[-1]
            print(symbol, 'BUY')

            sl, tp, volume, price = SLTP(symbol, mt5.ORDER_TYPE_BUY, balance, df)

            res = PURCHASE(symbol = symbol,
                        type = mt5.ORDER_TYPE_BUY,
                        balance = balance,
                        df = df,
                        sl = sl,
                        tp = tp,
                        volume = volume,
                        price = price)
                        
    elif latest['open'] > latest['close']:
        c1 = latest['close'] < lower.iloc[-1]
        c2 = latest['RSI'] > 50
        c3 = distance.iloc[-2] > distance.iloc[-1]
        if all([c1, c2, c3]):
            sl = middle.iloc[-1]
            print(symbol, 'SELL')

            sl, tp, volume, price = SLTP(symbol, mt5.ORDER_TYPE_SELL, balance, df)

            res = PURCHASE(symbol = symbol,
                        type = mt5.ORDER_TYPE_SELL,
                        balance = balance,
                        df = df,
                        sl = sl,
                        tp = tp,
                        volume = volume,
                        price = price)

    

if __name__ == '__main__':
    account = ACC NUMBER
    password = ACC PASSWORD
    server = ACC SERVER

    mt5.initialize(path="C:/Program Files/MetaTrader 5/terminal64.exe", timeout=180000)

    authorized = mt5.login(account, password, server)
    
    account_info = mt5.account_info()

    stocks = ['EURUSD','USDJPY','GBPUSD','AUDUSD','NZDUSD','EURJPY','GBPJPY', 'AUDJPY']
    timeLive = 0

    while True:

        balance = account_info.balance
        
        trade = False
        for ticker in stocks:
            df = DATA(ticker)
            S5(df, ticker, balance)
        if trade == False:
            print('No trade taken')
        print(mt5.last_error())    
        time.sleep(60)
        timeLive += 1
        print(f'Time live: {timeLive}')
            
