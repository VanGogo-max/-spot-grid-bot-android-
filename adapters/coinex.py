# adapters/coinex.py
import time
import hashlib
import hmac
import requests
from config import COINEX_ACCESS_ID, COINEX_SECRET_KEY

BASE_URL = "https://api.coinex.com/v1"

class CoinExSpot:
    name = "CoinEx"
    enabled = bool(COINEX_ACCESS_ID and COINEX_SECRET_KEY)
    maker_fee = 0.001  # 0.1%

    def _sign(self, params):
        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        to_sign = query_string + f"&secret_key={COINEX_SECRET_KEY}"
        return hashlib.md5(to_sign.encode()).hexdigest().upper()

    def _request(self, method, endpoint, params=None):
        params = params or {}
        params["access_id"] = COINEX_ACCESS_ID
        params["tonce"] = str(int(time.time() * 1000))

        sign = self._sign(params)
        params["signature"] = sign
        url = f"{BASE_URL}{endpoint}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        resp = requests.get(url)  # Всички заявки в CoinEx са GET
        return resp.json()

    def get_balance(self, asset="USDT"):
        data = self._request("GET", "/balance")
        balances = data.get("data", {})
        if asset in balances:
            return float(balances[asset]["available"])
        return 0.0

    def get_price(self, symbol):
        r = requests.get(f"{BASE_URL}/market/ticker", params={"market": symbol.replace("/", "")})
        return float(r.json()["data"]["ticker"]["last"])

    def place_order(self, symbol, side, price, qty):
        market = symbol.replace("/", "")
        return self._request("POST", "/order/limit", {
            "market": market,
            "type": side.lower(),
            "amount": f"{qty:.8f}",
            "price": f"{price:.8f}"
        })

    def get_klines(self, symbol, interval="1hour", limit=100):
        interval_map = {
            "1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
            "1h": "1hour", "4h": "4hour", "6h": "6hour", "12h": "12hour", "1d": "1day"
        }
        intvl = interval_map.get(interval, "1hour")
        r = requests.get(f"{BASE_URL}/market/kline", params={
            "market": symbol.replace("/", ""),
            "type": intvl,
            "limit": str(limit)
        })
        data = r.json().get("data", [])
        return [float(k[2]) for k in data]  # close price
