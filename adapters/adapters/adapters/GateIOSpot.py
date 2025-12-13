# adapters/GateIOSpot.py
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode

from config import EXCHANGE_KEYS

class GateIOSpot:
    name = "Gate.io"
    maker_fee = 0.001

    def __init__(self):
        self.api_key = EXCHANGE_KEYS["gateio"]["api_key"]
        self.secret = EXCHANGE_KEYS["gateio"]["api_secret"]
        self.base_url = "https://api.gateio.ws/api/v4"

    def _sign(self, method, url, body=""):
        t = str(int(time.time()))
        s = hmac.new(self.secret.encode("utf-8"), f"{method}\n{url}\n{body}\n{t}".encode("utf-8"), hashlib.sha512)
        signature = s.hexdigest()
        return t, signature

    def _request(self, method, endpoint, params=None, signed=False, body=None):
        url = self.base_url + endpoint
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if params:
            query = urlencode(params)
            url += "?" + query
        else:
            query = ""
        if signed:
            t, sig = self._sign(method, endpoint + "?" + query if params else endpoint, body or "")
            headers.update({
                "KEY": self.api_key,
                "Timestamp": t,
                "SIGN": sig
            })
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=10)
            else:
                resp = requests.post(url, headers=headers, json=body, timeout=10)
            return resp.json()
        except Exception as e:
            raise Exception(f"Gate.io error: {e}")

    def is_active(self):
        try:
            self._request("GET", "/spot/ping")
            return True
        except:
            return False

    def get_balance(self, asset):
        data = self._request("GET", "/spot/accounts", signed=True)
        for acc in data:
            if acc["currency"] == asset:
                return float(acc["available"])
        return 0.0

    def get_ticker(self, symbol):
        data = self._request("GET", "/spot/tickers", {"currency_pair": symbol.replace("/", "_")})
        ticker = data[0]
        return {"bidPrice": ticker["highest_bid"], "askPrice": ticker["lowest_ask"]}

    def get_price(self, symbol):
        return float(self.get_ticker(symbol)["bidPrice"])

    def get_klines(self, symbol, interval="1h", limit=50):
        symbol = symbol.replace("/", "_")
        interval_map = {"1h": "1h", "4h": "4h", "1d": "1d"}
        data = self._request("GET", "/spot/candlesticks", {
            "currency_pair": symbol,
            "interval": interval_map[interval],
            "limit": str(limit)
        })
        # Gate.io връща: [timestamp, volume, close, high, low, open]
        return [[float(c[0]), float(c[5]), float(c[3]), float(c[4]), float(c[2]), float(c[1])] for c in data]

    def get_symbol_info(self, symbol):
        symbol = symbol.replace("/", "_")
        data = self._request("GET", "/spot/currency_pairs", {"currency_pair": symbol})
        pair = data[0]
        return {
            "min_qty": float(pair["min_base_amount"]),
            "quantity_precision": len(pair["amount_precision"]),
            "price_precision": len(pair["precision"])
        }

    def place_order(self, symbol, side, price, qty):
        symbol = symbol.replace("/", "_")
        body = {
            "currency_pair": symbol,
            "type": "limit",
            "account": "spot",
            "side": side.lower(),
            "price": str(price),
            "amount": str(qty)
        }
        return self._request("POST", "/spot/orders", body=body, signed=True)

    def get_order_status(self, symbol, order_id):
        symbol = symbol.replace("/", "_")
        data = self._request("GET", f"/spot/orders/{order_id}", {"currency_pair": symbol}, signed=True)
        return data.get("status", "")

    def get_my_trades(self, symbol, order_id):
        symbol = symbol.replace("/", "_")
        data = self._request("GET", "/spot/my_trades", {"currency_pair": symbol, "order_id": str(order_id)}, signed=True)
        return [{"qty": t["amount"], "quoteQty": t["quote_amount"]} for t in data]

    def get_open_orders(self, symbol=None):
        params = {}
        if symbol:
            params["currency_pair"] = symbol.replace("/", "_")
        data = self._request("GET", "/spot/open_orders", params, signed=True)
        return [{"orderId": t["id"]} for t in data]

    def cancel_order(self, symbol, order_id):
        symbol = symbol.replace("/", "_")
        return self._request("DELETE", f"/spot/orders/{order_id}", {"currency_pair": symbol}, signed=True)
