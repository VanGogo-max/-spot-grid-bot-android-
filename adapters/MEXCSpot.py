# adapters/MEXCSpot.py
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode

from config import EXCHANGE_KEYS

class MEXCSpot:
    name = "MEXC"
    maker_fee = 0.001

    def __init__(self):
        self.api_key = EXCHANGE_KEYS["mexc"]["api_key"]
        self.secret = EXCHANGE_KEYS["mexc"]["api_secret"]
        self.base_url = "https://api.mexc.com"

    def _sign(self, params):
        ts = str(int(time.time() * 1000))
        params["timestamp"] = ts
        query = urlencode(sorted(params.items()))
        signature = hmac.new(self.secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
        return query + "&signature=" + signature

    def _request(self, method, endpoint, params=None, signed=False):
        url = self.base_url + endpoint
        headers = {"X-MEXC-APIKEY": self.api_key}
        if signed:
            query = self._sign(params or {})
            url += "?" + query
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=10)
            else:
                resp = requests.post(url, headers=headers, timeout=10)
            return resp.json()
        except Exception as e:
            raise Exception(f"MEXC error: {e}")

    def is_active(self):
        try:
            self._request("GET", "/api/v3/ping")
            return True
        except:
            return False

    def get_balance(self, asset):
        data = self._request("GET", "/api/v3/account", signed=True)
        for bal in data.get("balances", []):
            if bal["asset"] == asset:
                return float(bal["free"])
        return 0.0

    def get_ticker(self, symbol):
        symbol = symbol.replace("/", "")
        data = self._request("GET", "/api/v3/ticker/bookTicker", {"symbol": symbol})
        return {
            "bidPrice": data["bidPrice"],
            "askPrice": data["askPrice"]
        }

    def get_price(self, symbol):
        return float(self.get_ticker(symbol)["bidPrice"])

    def get_klines(self, symbol, interval="1h", limit=50):
        symbol = symbol.replace("/", "")
        interval_map = {"1h": "60m", "4h": "4h", "1d": "1d"}
        data = self._request("GET", "/api/v3/klines", {
            "symbol": symbol,
            "interval": interval_map.get(interval, "60m"),
            "limit": str(limit)
        })
        # Връща: [open_time, open, high, low, close, volume, ...]
        return [[float(x) for x in candle[:6]] for candle in data]

    def get_symbol_info(self, symbol):
        symbol = symbol.replace("/", "")
        data = self._request("GET", "/api/v3/exchangeInfo")
        for s in data["symbols"]:
            if s["symbol"] == symbol:
                filters = {f["filterType"]: f for f in s["filters"]}
                min_qty = float(filters["LOT_SIZE"]["minQty"])
                step_size = filters["LOT_SIZE"]["stepSize"]
                qty_prec = len(step_size.rstrip('0').split('.')[-1]) if '.' in step_size else 0

                tick_size = filters["PRICE_FILTER"]["tickSize"]
                price_prec = len(tick_size.rstrip('0').split('.')[-1]) if '.' in tick_size else 0

                return {
                    "min_qty": min_qty,
                    "quantity_precision": qty_prec,
                    "price_precision": price_prec
                }
        return {"min_qty": 0.01, "quantity_precision": 2, "price_precision": 4}

    def place_order(self, symbol, side, price, qty):
        symbol = symbol.replace("/", "")
        return self._request("POST", "/api/v3/order", {
            "symbol": symbol,
            "side": side.upper(),
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": str(qty),
            "price": str(price)
        }, signed=True)

    def get_order_status(self, symbol, order_id):
        symbol = symbol.replace("/", "")
        data = self._request("GET", "/api/v3/order", {"symbol": symbol, "orderId": str(order_id)}, signed=True)
        return data.get("status", "").lower()

    def get_my_trades(self, symbol, order_id):
        symbol = symbol.replace("/", "")
        data = self._request("GET", "/api/v3/myTrades", {"symbol": symbol, "orderId": str(order_id)}, signed=True)
        return [{"qty": t["qty"], "quoteQty": t["quoteQty"]} for t in data]

    def get_open_orders(self, symbol=None):
        params = {}
        if symbol:
            params["symbol"] = symbol.replace("/", "")
        data = self._request("GET", "/api/v3/openOrders", params, signed=True)
        return [{"orderId": t["orderId"]} for t in data]

    def cancel_order(self, symbol, order_id):
        symbol = symbol.replace("/", "")
        return self._request("DELETE", "/api/v3/order", {"symbol": symbol, "orderId": str(order_id)}, signed=True)
