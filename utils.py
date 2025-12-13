# utils.py
import numpy as np
import pandas as pd
from ta.trend import ADXIndicator, SMAIndicator
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator

def klines_to_dataframe(klines):
    """
    Преобразува списък от свещи (open, high, low, close, volume) в pandas DataFrame.
    Очаква формат: [[ts, open, high, low, close, volume], ...]
    """
    if not klines or len(klines[0]) < 6:
        return None
    df = pd.DataFrame(klines, columns=["timestamp", "open", "high", "low", "close", "volume"])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.dropna(inplace=True)
    return df

def is_safe_market(klines, min_avg_volume_usdt=5000):
    """
    Проверява дали пазарът е достатъчно ликвиден.
    """
    df = klines_to_dataframe(klines)
    if df is None or len(df) < 10:
        return False
    avg_vol = df["volume"].tail(10).mean()
    return avg_vol >= min_avg_volume_usdt

def is_market_trending(klines, adx_threshold=20, rsi_neutral_range=(35, 65)):
    """
    Определя дали има значим тренд:
    - ADX > adx_threshold → силен тренд
    - RSI извън прегрято/предозаредено → по-добра входна точка
    """
    df = klines_to_dataframe(klines)
    if df is None or len(df) < 20:
        return False

    # ADX (Trend Strength)
    adx = ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=14)
    df["adx"] = adx.adx()

    # RSI (Momentum)
    rsi = RSIIndicator(close=df["close"], window=14)
    df["rsi"] = rsi.rsi()

    latest_adx = df["adx"].iloc[-1]
    latest_rsi = df["rsi"].iloc[-1]

    strong_trend = latest_adx > adx_threshold
    not_overbought = latest_rsi < rsi_neutral_range[1]  # не над 65
    not_oversold = latest_rsi > rsi_neutral_range[0]   # не под 35

    return strong_trend and not_overbought and not_oversold
