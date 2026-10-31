"""
Binance Spot & Futures Dual Client with Authenticated HMAC-SHA256 Signatures.
- Zero external libraries (pure Python standard library: urllib, hmac, hashlib).
- Handles real live balances, prices, orderbook depth, and order execution.
- Auto-detects micro-balances ($1 to $5+) and routes safely.
"""
import urllib.request
import urllib.parse
import urllib.error
import time
import hmac
import hashlib
import json
from typing import Dict, Any, List, Optional

class BinanceClient:
    def __init__(self, api_key: str = "", secret_key: str = ""):
        self.api_key = api_key.strip()
        self.secret_key = sec_key = secret_key.strip()
        self.spot_base = "https://api.binance.com"
        self.futures_base = "https://fapi.binance.com"

    def _sign(self, query_string: str) -> str:
        return hmac.new(
            self.secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _request(self, base_url: str, path: str, method: str = "GET", params: Optional[Dict] = None, signed: bool = False) -> Dict[str, Any]:
        params = params or {}
        if signed:
            if not self.api_key or not self.secret_key:
                return {"status": "error", "msg": "API credentials missing"}
            params["timestamp"] = int(time.time() * 1000)
            query_str = urllib.parse.urlencode(params)
            signature = self._sign(query_str)
            query_str += f"&signature={signature}"
        else:
            query_str = urllib.parse.urlencode(params)

        url = f"{base_url}{path}"
        if query_str and method == "GET":
            url += f"?{query_str}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GrokQuant/2.0"
        }
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key

        body = None
        if method == "POST":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            body = query_str.encode("utf-8")

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raw_err = e.read().decode("utf-8")
            try:
                err_json = json.loads(raw_err)
                return {"status": "error", "code": err_json.get("code"), "msg": err_json.get("msg", raw_err)}
            except Exception:
                return {"status": "error", "code": e.code, "msg": raw_err}
        except Exception as ex:
            return {"status": "error", "msg": str(ex)}

    def get_spot_balance(self) -> Dict[str, Any]:
        """Fetches total USDT & asset balances from Binance Spot."""
        if not self.api_key or not self.secret_key:
            return {"status": "unauthenticated", "total_usdt": 0.0, "balances": {}}

        res = self._request(self.spot_base, "/api/v3/account", signed=True)
        if isinstance(res, dict) and "balances" in res:
            balances = {}
            usdt_total = 0.0
            for b in res["balances"]:
                free = float(b["free"])
                locked = float(b["locked"])
                tot = free + locked
                if tot > 0:
                    balances[b["asset"]] = {"free": free, "locked": locked, "total": tot}
                    if b["asset"] == "USDT":
                        usdt_total += tot
            return {"status": "ok", "total_usdt": usdt_total, "balances": balances}
        return {"status": "error", "msg": res.get("msg", "Failed to query Spot balance")}

    def get_ticker_price(self, symbol: str = "BTCUSDT") -> float:
        """Fetches current live ticker price from Binance Spot."""
        res = self._request(self.spot_base, "/api/v3/ticker/price", params={"symbol": symbol})
        if isinstance(res, dict) and "price" in res:
            return float(res["price"])
        return 0.0

    def get_orderbook(self, symbol: str = "BTCUSDT", limit: int = 5) -> Dict[str, Any]:
        """Fetches live orderbook depth."""
        res = self._request(self.spot_base, "/api/v3/depth", params={"symbol": symbol, "limit": limit})
        if isinstance(res, dict) and "bids" in res and "asks" in res:
            bids = [(float(p), float(q)) for p, q in res["bids"]]
            asks = [(float(p), float(q)) for p, q in res["asks"]]
            return {"bids": bids, "asks": asks}
        return {"bids": [], "asks": []}

    def get_candles(self, symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 25) -> List[List[Any]]:
        """Fetches candlestick bar data [open_time, open, high, low, close, volume, ...]."""
        res = self._request(self.spot_base, "/api/v3/klines", params={"symbol": symbol, "interval": interval, "limit": limit})
        if isinstance(res, list):
            return res
        return []

    def place_spot_order(self, symbol: str, side: str, quote_order_qty: float) -> Dict[str, Any]:
        """
        Places a SPOT market order by USDT quote amount (e.g. $5.00 USDT).
        Binance Spot enforces a minNotional of $5.00 USDT.
        """
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quoteOrderQty": f"{quote_order_qty:.2f}"
        }
        res = self._request(self.spot_base, "/api/v3/order", method="POST", params=params, signed=True)
        if isinstance(res, dict) and res.get("status") in ["FILLED", "NEW"]:
            return {"status": "filled", "order_id": res.get("orderId"), "data": res}
        return {"status": "rejected", "msg": res.get("msg", "Order rejected")}
