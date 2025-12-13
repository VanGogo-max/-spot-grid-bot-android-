# adapters/kucoin.py
import time
import hmac
import hashlib
import requests
import base64
import json
from urllib.parse import urlencode
from config import KUCOIN_API_KEY, KUCOIN_SECRET_KEY, KUCOIN_PASSPHRASE

BASE_URL = "https://api.kucoin.com"

class KuCoinSpot:
    name = "KuCoin"
    enabled = bool(KUCOIN_API_KEY and KUCOIN_SECRET_KEY and KUCOIN_PASSPHRASE)
    maker_fee = 0.001  # 0.1%

    def _request(self, method, path, params=None):
        params = params or {}
        now = int(time.time() * 1000)
        url_path = path
        if method == "GET" and params:
            url_path += "?" + urlencode(params)
            body = ""
        elif method == "POST":
            body = json.dumps(params)
        else:
            body = ""

        str_to_sign = str(now) + method + url_path
        if method == "POST":
            str_to_sign = str(now) + method + path + body

        signature = base64.b64encode(
            hmac.new(KUCOIN_SECRET_KEY.encode(), str_to_sign.encode(), hashlib.sha256).digest()
        ).decode()
        headers = {
            "KC-API-KEY": KUCOIN_API_KEY,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "KC-API-PASSPHRASE": KUCOIN_PASSPHRASE,
            "Content-Type": "application/json"
        }
        url = BASE_URL + path
        fn = requests.get if method == "GET" else requests.post
        return fn(url, headers=headers, json=params if method == "POST" else None).json()

    def get_balance(self, asset="USDT"):
        r = self._request("GET", "/api/v1/accounts", {"currency": asset, "type": "trade"})
        if r.get("data"):
            return float(r["data"][0]["available"])
        return 0.0

    def get_price(self, symbol):
        r = requests.get(f"{BASE_URL}/api/v1/market/orderbook/level1?symbol={symbol}")
        return float(r.json()["data"]["price"])

    def place_order(self, symbol, side, price, qty):
        return self._request("POST", "/api/v1/orders", {
            "clientOid": str(int(time.time() * 1000)),
            "side": side.lower(),
            "symbol": symbol,
            "type": "limit",
            "price": str(price),
            "size": str(qty)
        })

    def get_klines(self, symbol, interval="1hour", limit=100):
        from utils import get_klines_rest
        return get_klines_rest(f"{BASE_URL}/api/v1/klines", symbol, interval, limit)
