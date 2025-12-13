# adapters/KuCoinSpot.py
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode

from config import EXCHANGE_KEYS

class KuCoinSpot:
    name = "KuCoin"
    maker_fee = 0.0008

    def __init__(self):
        self.api_key = EXCHANGE_KEYS["kucoin"]["api_key"]
        self.secret = EXCHANGE_KEYS["kucoin"]["api_secret"]
        self.passphrase = EXCHANGE_KEYS["kucoin"]["api_passphrase"]
        self.base_url = "https://api.kucoin.com"

    def _sign(self, method, endpoint, params=None):
        now = int(time.time() * 1000)
        str_to_sign = str(now) + method + endpoint
        if params:
            query = urlencode(params)
            str_to_sign += "?" + query
        signature = hmac.new(self.secret.encode("utf-8"), str_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        return {
            "KC-API-KEY": self.api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "KC-API-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json"
        }

    def _request(self, method, endpoint, params=None, signed=False):
        url = self.base_url + endpoint
        headers = {}
        if signed:
            headers = self._sign(method, endpoint, params)
        try:
            if method == "GET":
                resp = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                resp = requests.post(url, json=params, headers=headers, timeout=10)
            data = resp.json()
            return data["data"]
        except Exception as e:
            raise Exception(f"KuCoin error: {e}")

    def is_active(self):
        try:
            self._request("GET", "/api/v1/timestamp")
            return True
        except:
            return False

    def get_balance(self, asset):
        data = self._request("GET", "/api/v1/accounts", {"currency": asset, "type": "trade"}, signed=True)
        if data:
            return float(data[0]["available"])
        return 0.0

    def get_ticker(self, symbol):
        data = self._request("GET", "/api/v1/market/orderbook/level1", {"symbol": symbol.replace("/", "-")})
        return {"bidPrice": data["bestBid"], "askPrice": data["bestAsk"]}

    def get_price(self, symbol):
        return float(self.get_ticker(symbol)["bidPrice"])

    def get_klines(self, symbol, interval="1h", limit=50):
        symbol = symbol.replace("/", "-")
        interval_map = {"1h": "1hour", "4h": "4hour", "1d": "1day"}
        data = self._request("GET", "/api/v1/market/candles", {
            "symbol": symbol,
            "type": interval_map[interval],
            "startAt": int(time.time()) - limit * 3600,
            "endAt": int(time.time())
        })
        # KuCoin: [time, open, close, high, low, volume, turnover]
        return [[float(c[0]), float(c[1]), float(c[3]), float(c[4]), float(c[2]), float(c[5])] for c in data]

    def get_symbol_info(self, symbol):
        symbol = symbol.replace("/", "-")
        data = self._request("GET", "/api/v1/symbols")
        for s in data:
            if s["symbol"] == symbol:
                return {
                    "min_qty": float(s["baseMinSize"]),
                    "quantity_precision": len(s["baseIncrement"].rstrip('0').split('.')[-1]),
                    "price_precision": len(s["priceIncrement"].rstrip('0').split('.')[-1])
                }
        return {"min_qty": 0.01, "quantity_precision": 2, "price_precision": 4}

    def place_order(self, symbol, side, price, qty):
        symbol = symbol.replace("/", "-")
        params = {
            "clientOid": str(int(time.time() * 1000)),
            "side": side.lower(),
            "symbol": symbol,
            "type": "limit",
            "price": str(price),
            "size": str(qty)
        }
        return self._request("POST", "/api/v1/orders", params, signed=True)

    def get_order_status(self, symbol, order_id):
        data = self._request("GET", f"/api/v1/orders/{order_id}", signed=True)
        return data.get("status", "")

    def get_my_trades(self, symbol, order_id):
        data = self._request("GET", "/api/v1/fills", {"orderId": str(order_id)}, signed=True)
        return [{"qty": t["size"], "quoteQty": str(float(t["size"]) * float(t["price"]))} for t in data["items"]]

    def get_open_orders(self, symbol=None):
        params = {}
        if symbol:
            params["symbol"] = symbol.replace("/", "-")
        data = self._request("GET", "/api/v1/orders", params, signed=True)
        return [{"orderId": t["id"]} for t in data["items"]]

    def cancel_order(self, symbol, order_id):
        return self._request("DELETE", f"/api/v1/orders/{order_id}", signed=True)
