from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import urllib.error
import time
import hmac
import hashlib

# Binance Global multi-cluster endpoints
BINANCE_ENDPOINTS = [
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://api.binance.com"
]

# Precision map for Binance Spot base assets
SYMBOL_PRECISION = {
    "BTCUSDT": 5,
    "ETHUSDT": 4,
    "SOLUSDT": 2,
    "BNBUSDT": 3
}

class handler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-MBX-APIKEY')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "online",
            "service": "Grok Bot Binance Proxy Serverless API",
            "timestamp": int(time.time() * 1000)
        }).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        
        try:
            data = json.loads(body)
        except Exception as e:
            self._respond_json(400, {"success": False, "error": "Invalid JSON: " + str(e)})
            return

        action = data.get("action", "test_connection")
        api_key = data.get("apiKey", "").strip()
        api_secret = data.get("apiSecret", "").strip()

        if not api_key or not api_secret:
            self._respond_json(400, {
                "success": False,
                "error": "Missing Binance API Key or Secret Key"
            })
            return

        if action == "test_connection" or action == "get_balance":
            self.handle_test_connection(api_key, api_secret)
        elif action == "create_order":
            self.handle_create_order(api_key, api_secret, data)
        else:
            self._respond_json(400, {"success": False, "error": f"Unknown action: {action}"})

    def handle_test_connection(self, api_key, api_secret):
        timestamp = int(time.time() * 1000)
        query_string = f"timestamp={timestamp}&recvWindow=5000"
        signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

        last_error = None
        for base_url in BINANCE_ENDPOINTS:
            full_url = f"{base_url}/api/v3/account?{query_string}&signature={signature}"
            req = urllib.request.Request(full_url, headers={
                'X-MBX-APIKEY': api_key,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            try:
                with urllib.request.urlopen(req, timeout=6) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    can_trade = res_data.get("canTrade", False)
                    account_type = res_data.get("accountType", "SPOT")
                    permissions = res_data.get("permissions", [])
                    
                    usdt_free = 0.0
                    balances = []
                    for b in res_data.get("balances", []):
                        free = float(b.get("free", 0))
                        locked = float(b.get("locked", 0))
                        if b.get("asset") == "USDT":
                            usdt_free = round(free, 2)
                        if free > 0 or locked > 0:
                            balances.append({
                                "asset": b.get("asset"),
                                "free": round(free, 6),
                                "locked": round(locked, 6)
                            })

                    balances.sort(key=lambda x: 0 if x["asset"] == "USDT" else 1)

                    self._respond_json(200, {
                        "success": True,
                        "canTrade": can_trade,
                        "accountType": account_type,
                        "permissions": permissions,
                        "usdtBalance": usdt_free,
                        "balances": balances[:10],
                        "message": f"Binance connected successfully! Real USDT Balance: ${usdt_free:.2f}"
                    })
                    return
            except urllib.error.HTTPError as e:
                try:
                    err_data = json.loads(e.read().decode('utf-8'))
                    err_msg = err_data.get("msg", str(e))
                    err_code = err_data.get("code", e.code)
                except Exception:
                    err_msg = str(e)
                    err_code = e.code
                last_error = {"code": err_code, "msg": err_msg}
                # If it's a restricted location error, try next endpoint in cluster
                if "restricted location" in str(err_msg).lower():
                    continue
                else:
                    break
            except Exception as e:
                last_error = {"code": 500, "msg": str(e)}
                continue

        # If all cluster endpoints failed
        err_msg = last_error.get("msg", "Connection failed") if last_error else "Connection failed"
        err_code = last_error.get("code", 500) if last_error else 500

        # Helpful hint if cloud IP is restricted
        if "restricted location" in str(err_msg).lower():
            err_msg += " (Tip: Cloud server IP is restricted by Binance. Run 'python server.py' locally on your machine for 100% direct Pakistan-to-Binance unrestricted trading!)"

        self._respond_json(200, {
            "success": False,
            "code": err_code,
            "error": f"Binance rejected: {err_msg}"
        })

    def handle_create_order(self, api_key, api_secret, data):
        symbol = data.get("symbol", "BTCUSDT").upper()
        side = data.get("side", "BUY").upper()
        order_type = data.get("type", "MARKET").upper()
        quote_order_qty = data.get("quoteOrderQty")
        quantity = data.get("quantity")

        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "timestamp": int(time.time() * 1000),
            "recvWindow": 5000
        }

        decimals = SYMBOL_PRECISION.get(symbol, 4)

        if side == "BUY":
            if quote_order_qty:
                params["quoteOrderQty"] = f"{float(quote_order_qty):.2f}"
            elif quantity:
                params["quantity"] = f"{float(quantity):.{decimals}f}"
            else:
                params["quoteOrderQty"] = "10.00"
        else: # SELL
            if quantity:
                params["quantity"] = f"{float(quantity):.{decimals}f}"
            elif quote_order_qty:
                params["quoteOrderQty"] = f"{float(quote_order_qty):.2f}"
            else:
                self._respond_json(400, {"success": False, "error": "Must specify quantity or quoteOrderQty for SELL"})
                return

        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

        last_error = None
        for base_url in BINANCE_ENDPOINTS:
            full_url = f"{base_url}/api/v3/order?{query_string}&signature={signature}"
            req = urllib.request.Request(full_url, data=b"", headers={
                'X-MBX-APIKEY': api_key,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, method="POST")

            try:
                with urllib.request.urlopen(req, timeout=6) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    self._respond_json(200, {
                        "success": True,
                        "order": res_data,
                        "message": f"Binance Spot order executed: {side} {symbol}"
                    })
                    return
            except urllib.error.HTTPError as e:
                try:
                    err_data = json.loads(e.read().decode('utf-8'))
                    err_msg = err_data.get("msg", str(e))
                    err_code = err_data.get("code", e.code)
                except Exception:
                    err_msg = str(e)
                    err_code = e.code
                last_error = {"code": err_code, "msg": err_msg}
                if "restricted location" in str(err_msg).lower():
                    continue
                else:
                    break
            except Exception as e:
                last_error = {"code": 500, "msg": str(e)}
                continue

        err_msg = last_error.get("msg", "Order execution failed") if last_error else "Order failed"
        err_code = last_error.get("code", 500) if last_error else 500
        self._respond_json(200, {
            "success": False,
            "code": err_code,
            "error": f"Binance order error: {err_msg}"
        })

    def _respond_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
