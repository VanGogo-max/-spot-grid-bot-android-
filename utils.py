# utils.py
import numpy as np
import requests

def get_klines_rest(url, symbol, interval="1h", limit=100):
    try:
        clean_symbol = symbol.replace("/", "")
        resp = requests.get(url, params={"symbol": clean_symbol, "interval": interval, "limit": limit}, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if isinstance(data, list):
            return [float(k[4]) for k in data]  # close price
        return []
    except Exception:
        return []

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def is_safe_market(prices):
    if len(prices) < 50:
        return False
    current = prices[-1]
    ma200 = np.mean(prices[-min(200, len(prices)):])
    rsi = calculate_rsi(prices)
    return current > ma200 and 45 <= rsi <= 70

def is_market_trending(prices, period=20, min_bandwidth=0.005):
    """Проверява дали пазарът е достатъчно волатилен за търговия"""
    if len(prices) < period:
        return False
    std = np.std(prices[-period:])
    avg = np.mean(prices[-period:])
    bandwidth = std / avg if avg > 0 else 0
    return bandwidth >= min_bandwidth
