# adapters/CoinExSpot.py
import time
import hashlib
import hmac
import requests
from urllib.parse import urlencode

from config import EXCHANGE_KEYS

class CoinExSpot:
    name = "CoinEx"
    maker_fee = 0.001  # 0.1%

    def __init__(self):
        self.access_id = EXCHANGE_KEYS["coinex"]["access_id"]
        self.secret_key = EXCHANGE_KEYS["coinex"]["secret_key"]
        self.base_url = "https://api.coinex.com/v1"

    def _sign(self, params):
        """Генерира подпис според CoinEx изискванията."""
        params["access_id"] = self.access_id
        params["tonce"] = str(int(time.time() * 1000))
        # Сортиране по ключ
        query_string = urlencode(sorted(params.items()))
        to_sign = f"{query_string}&secret_key={self.secret_key}"
        return hashlib.md5(to_sign.encode("utf-8")).hexdigest().upper()

    def _request(self, method, endpoint, params=None, signed=False):
        url = self.base_url + endpoint
        headers = {"Content-Type": "application/json"}
        if signed:
            if params is None:
                params = {}
            params["signature"] = self._sign(params.copy())
        try:
            if method == "GET":
                resp = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                resp = requests.post(url, json=params, headers=headers, timeout=10)
            return resp.json()
        except Exception as e:
            raise Exception(f"CoinEx API error: {e}")

    def is_active(self):
        try:
            self._request("GET", "/market/ticker", {"market": "BTCUSDT"})
            return True
        except:
            return False

    def get_balance(self, asset):
        data = self._request("GET", "/balance", signed=True)
        if data.get("code") == 0:
            return float(data["data"].get(asset, {}).get("available", 0))
        return 0.0

    def get_price(self, symbol):
        market = symbol.replace("/", "")
        data = self._request("GET", "/market/ticker", {"market": market})
        if data.get("code") == 0:
            return float(data["data"]["ticker"]["last"])
        raise Exception("Price fetch failed")

    def get_ticker(self, symbol):
        market = symbol.replace("/", "")
        data = self._request("GET", "/market/ticker", {"market": market})
        if data.get("code") == 0:
            ticker = data["data"]["ticker"]
            return {
                "bidPrice": ticker["buy"],
                "askPrice": ticker["sell"]
            }
        raise Exception("Ticker fetch failed")

    def get_klines(self, symbol, interval="1h", limit=50):
        market = symbol.replace("/", "")
        interval_map = {"1h": "60", "4h": "240", "1d": "86400"}
        period = interval_map.get(interval, "60")
        data = self._request("GET", "/market/kline", {
            "market": market,
            "type": period,
            "limit": str(limit)
        })
        if data.get("code") == 0:
            # Връща списък от затварящи цени (последната колона = close)
            return [float(kline[2]) for kline in data["data"]]
        return []

    def get_symbol_info(self, symbol):
        market = symbol.replace("/", "")
        # CoinEx не дава официално min_qty през API → използваме хардкод за популярни монети
        info_map = {
            "BTCUSDT": {"min_qty": 0.0001, "quantity_precision": 4, "price_precision": 2},
            "ETHUSDT": {"min_qty": 0.001, "quantity_precision": 3, "price_precision": 2},
            "SOLUSDT": {"min_qty": 0.01, "quantity_precision": 2, "price_precision": 3},
            "XRPUSDT": {"min_qty": 1.0, "quantity_precision": 1, "price_precision": 4},
            "DOGEUSDT": {"min_qty": 10.0, "quantity_precision": 0, "price_precision": 5},
        }
        return info_map.get(market, {"min_qty": 0.01, "quantity_precision": 2, "price_precision": 4})

    def place_order(self, symbol, side, price, qty):
        market = symbol.replace("/", "")
        params = {
            "market": market,
            "type": "limit",
            "side": side.lower(),
            "amount": str(qty),
            "price": str(price)
        }
        return self._request("POST", "/order/limit", params, signed=True)

    def get_order_status(self, symbol, order_id):
        market = symbol.replace("/", "")
        data = self._request("GET", "/order/status", {
            "market": market,
            "id": str(order_id)
        }, signed=True)
        if data.get("code") == 0:
            status = data["data"]["status"]
            return "filled" if status == "done" else "canceled" if status in ("cancel", "failed") else "open"
        return "unknown"

    def get_open_orders(self, symbol=None):
        market = symbol.replace("/", "") if symbol else "BTCUSDT"
        data = self._request("GET", "/order/pending", {"market": market}, signed=True)
        if data.get("code") == 0:
            return [{"orderId": item["id"]} for item in data["data"]["data"]]
        return []

    def cancel_order(self, symbol, order_id):
        market = symbol.replace("/", "")
        return self._request("DELETE", "/order/pending", {
            "market": market,
            "id": str(order_id)
        }, signed=True)

    def get_my_trades(self, symbol, order_id):
        market = symbol.replace("/", "")
        data = self._request("GET", "/order/deals", {
            "market": market,
            "order_id": str(order_id)
        }, signed=True)
        if data.get("code") == 0:
            return [{"qty": t["amount"], "quoteQty": t["deal_money"]} for t in data["data"]["data"]]
        return []
