# adapters/mexc.py
import time
import hmac
import hashlib
import requests
from config import MEXC_API_KEY, MEXC_SECRET_KEY

BASE_URL = "https://api.mexc.com"

class MEXCSpot:
    name = "MEXC"
    enabled = bool(MEXC_API_KEY and MEXC_SECRET_KEY)
    maker_fee = 0.001  # 0.1%

    def _sign(self, params):
        query = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
        return hmac.new(MEXC_SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()

    def _request(self, method, endpoint, params=None):
        params = params or {}
        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = self._sign(params)
        headers = {"X-MEXC-APIKEY": MEXC_API_KEY}
        url = BASE_URL + endpoint
        fn = requests.get if method == "GET" else requests.post
        return fn(url, headers=headers, params=params).json()

    def get_balance(self, asset="USDT"):
        data = self._request("GET", "/api/v3/account")
        for b in data.get("balances", []):
            if b["asset"] == asset:
                return float(b["free"])
        return 0.0

    def get_price(self, symbol):
        r = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol={symbol.replace('/', '')}")
        return float(r.json()["price"])

    def place_order(self, symbol, side, price, qty):
        return self._request("POST", "/api/v3/order", {
            "symbol": symbol.replace("/", ""),
            "side": side.upper(),
            "type": "LIMIT",
            "price": f"{price:.8f}",
            "quantity": f"{qty:.8f}",
            "timeInForce": "GTC"
        })

    def get_klines(self, symbol, interval="1h", limit=100):
        from utils import get_klines_rest
        return get_klines_rest(f"{BASE_URL}/api/v3/klines", symbol, interval, limit)
