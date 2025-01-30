from ta.momentum import RSIIndicator
import MetaTrader5 as mt5
import pandas as pd
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

def DATA(symbol, n=30):
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, n)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['ema_9'] = EMA(df = df['close'], n = 9)
    df['ema_21'] = EMA(df = df['close'], n = 21)
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
from ta.momentum import RSIIndicator
import MetaTrader5 as mt5
import pandas as pd
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

def DATA(symbol, n=30):
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, n)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['ema_9'] = EMA(df = df['close'], n = 9)
    df['ema_21'] = EMA(df = df['close'], n = 21)
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

    stop_loss_distance = info.trade_stops_level * info.point
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


def PURCHASE(symbol, type, balance, df):
    sl, tp, volume, price = SLTP(symbol, type, balance, df)
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
    df = DATA(symbol)
    latest = df.iloc[-1]
    previous = df.iloc[-2]

    if previous['ema_9'] < previous['ema_21'] and latest['ema_9'] > latest['ema_21'] and latest['RSI'] < 70:
        print(symbol, 'BUY')
        res = PURCHASE(symbol = symbol,
                       type = mt5.ORDER_TYPE_BUY,
                       balance = balance,
                       df = df)
    elif previous['ema_9'] > previous['ema_21'] and latest['ema_9'] < latest['ema_21'] and latest['RSI'] > 30:
        print(symbol, 'SELL')
        res = PURCHASE(symbol = symbol,
                       type = mt5.ORDER_TYPE_SELL,
                       balance = balance,
                       df = df)
    else:
        print('No trade')

if __name__ == '__main__':
    account = 58647600
    password = 'DnF*6sSc'
    server = 'AdmiralsGroup-Demo'

    mt5.initialize(path="C:/Program Files/MetaTrader 5/terminal64.exe", timeout=180000)

    authorized = mt5.login(account, password, server)
    
    account_info = mt5.account_info()

    stocks = ['EURUSD','USDJPY','GBPUSD','AUDUSD','NZDUSD','EURJPY','GBPJPY','USDMXN','AUDJPY']
    timeLive = 0

    while True:

        balance = account_info.balance
        
        for ticker in stocks:
            df = DATA(ticker)
            S1(df, ticker, balance)
        print(mt5.last_error())    
        time.sleep(60)
        timeLive += 1
        print(f'Time live: {timeLive}')
            

