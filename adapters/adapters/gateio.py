# adapters/gateio.py
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from config import GATEIO_API_KEY, GATEIO_SECRET_KEY

BASE_URL = "https://api.gateio.ws/api/v4"

class GateIOSpot:
    name = "Gate.io"
    enabled = bool(GATEIO_API_KEY and GATEIO_SECRET_KEY)
    maker_fee = 0.001  # 0.1%

    def _sign(self, method, url, params={}):
        full_url = url
        if params:
            full_url += "?" + urlencode(params)
        body = ""
        sign_str = f"{method}\n{full_url}\n{body}"
        signature = hmac.new(
            GATEIO_SECRET_KEY.encode(),
            sign_str.encode(),
            hashlib.sha512
        ).hexdigest()
        return signature

    def _request(self, method, path, params=None):
        params = params or {}
        url = BASE_URL + path
        headers = {
            "KEY": GATEIO_API_KEY,
            "SIGN": self._sign(method, path, params)
        }
        fn = requests.get if method == "GET" else requests.post
        return fn(url, headers=headers, params=params).json()

    def get_balance(self, asset="USDT"):
        data = self._request("GET", "/spot/accounts")
        for acc in data:
            if acc["currency"] == asset:
                return float(acc["available"])
        return 0.0

    def get_price(self, symbol):
        r = requests.get(f"{BASE_URL}/spot/tickers?currency_pair={symbol}")
        return float(r.json()[0]["last"])

    def place_order(self, symbol, side, price, qty):
        return self._request("POST", "/spot/orders", {
            "currency_pair": symbol,
            "side": side.lower(),
            "type": "limit",
            "price": str(price),
            "amount": str(qty)
        })

    def get_klines(self, symbol, interval="1h", limit=100):
        from utils import get_klines_rest
        return get_klines_rest(f"{BASE_URL}/spot/candlesticks", symbol, interval, limit)
