from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import urllib.error
import time
import hmac
import hashlib

import math

# Binance Global multi-cluster endpoints
BINANCE_ENDPOINTS = [
    "https://api.binance.com",
    "https://api-gcp.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://api4.binance.com"
]

# Exact stepSize and precision for Binance Spot target pairs
SYMBOL_CONFIG = {
    "BTCUSDT":  {"stepSize": 0.00001, "decimals": 5, "baseAsset": "BTC",  "minNotional": 5.0},
    "ETHUSDT":  {"stepSize": 0.0001,  "decimals": 4, "baseAsset": "ETH",  "minNotional": 5.0},
    "SOLUSDT":  {"stepSize": 0.001,   "decimals": 3, "baseAsset": "SOL",  "minNotional": 5.0},
    "BNBUSDT":  {"stepSize": 0.001,   "decimals": 3, "baseAsset": "BNB",  "minNotional": 5.0},
    "XRPUSDT":  {"stepSize": 0.1,     "decimals": 1, "baseAsset": "XRP",  "minNotional": 5.0},
    "DOGEUSDT": {"stepSize": 1.0,     "decimals": 0, "baseAsset": "DOGE", "minNotional": 5.0},
    "SUIUSDT":  {"stepSize": 0.1,     "decimals": 1, "baseAsset": "SUI",  "minNotional": 5.0},
    "ADAUSDT":  {"stepSize": 0.1,     "decimals": 1, "baseAsset": "ADA",  "minNotional": 5.0},
    "AVAXUSDT": {"stepSize": 0.01,    "decimals": 2, "baseAsset": "AVAX", "minNotional": 5.0},
    "LINKUSDT": {"stepSize": 0.01,    "decimals": 2, "baseAsset": "LINK", "minNotional": 5.0},
    "PEPEUSDT": {"stepSize": 1000.0,  "decimals": 0, "baseAsset": "PEPE", "minNotional": 5.0},
    "WIFUSDT":  {"stepSize": 0.1,     "decimals": 1, "baseAsset": "WIF",  "minNotional": 5.0}
}

def get_binance_server_time():
    for base_url in BINANCE_ENDPOINTS:
        try:
            req = urllib.request.Request(f"{base_url}/api/v3/time", headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                st = data.get("serverTime")
                if st:
                    return int(st)
        except Exception:
            continue
    return int(time.time() * 1000)


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
        api_key = data.get("apiKey", "").strip().replace("\r", "").replace("\n", "")
        api_secret = data.get("apiSecret", "").strip().replace("\r", "").replace("\n", "")

        if not api_key or not api_secret:
            self._respond_json(400, {
                "success": False,
                "error": "Missing Binance API Key or Secret Key"
            })
            return

        market_type = data.get("marketType", "SPOT").upper()
        if action == "test_connection" or action == "get_balance":
            if market_type == "FUTURES":
                self.handle_futures_connection(api_key, api_secret)
            else:
                self.handle_test_connection(api_key, api_secret)
        elif action == "create_order":
            if market_type == "FUTURES":
                self.handle_create_futures_order(api_key, api_secret, data)
            else:
                self.handle_create_order(api_key, api_secret, data)
        else:
            self._respond_json(400, {"success": False, "error": f"Unknown action: {action}"})

    def handle_test_connection(self, api_key, api_secret):
        timestamp = get_binance_server_time()
        query_string = f"timestamp={timestamp}&recvWindow=60000"
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

    def _get_base_free_balance(self, api_key, api_secret, base_asset):
        timestamp = get_binance_server_time()
        query_string = f"timestamp={timestamp}&recvWindow=60000"
        signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

        for base_url in BINANCE_ENDPOINTS:
            full_url = f"{base_url}/api/v3/account?{query_string}&signature={signature}"
            req = urllib.request.Request(full_url, headers={
                'X-MBX-APIKEY': api_key,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    for b in res_data.get("balances", []):
                        if b.get("asset") == base_asset:
                            return float(b.get("free", 0.0))
                    return 0.0
            except Exception:
                continue
        return 0.0

    def handle_create_order(self, api_key, api_secret, data):
        symbol = data.get("symbol", "BTCUSDT").upper()
        side = data.get("side", "BUY").upper()
        order_type = data.get("type", "MARKET").upper()
        quote_order_qty = data.get("quoteOrderQty")
        quantity = data.get("quantity")

        cfg = SYMBOL_CONFIG.get(symbol, {
            "stepSize": 0.0001,
            "decimals": 4,
            "baseAsset": symbol.replace("USDT", ""),
            "minNotional": 5.0
        })
        decimals = cfg["decimals"]
        step_size = cfg["stepSize"]

        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "timestamp": get_binance_server_time(),
            "recvWindow": 60000
        }

        if side == "BUY":
            if quote_order_qty:
                params["quoteOrderQty"] = f"{float(quote_order_qty):.2f}"
            elif quantity:
                params["quantity"] = f"{float(quantity):.{decimals}f}"
            else:
                params["quoteOrderQty"] = "10.00"
        else: # SELL
            # Binance Spot MARKET SELL orders REQUIRE quantity (not quoteOrderQty)
            sell_qty = None
            if quantity and str(quantity).upper() != "ALL":
                try:
                    sell_qty = float(quantity)
                except ValueError:
                    sell_qty = None

            # If quantity not provided or "ALL", lookup free asset balance directly from Binance
            if sell_qty is None or sell_qty <= 0:
                sell_qty = self._get_base_free_balance(api_key, api_secret, cfg["baseAsset"])

            # Round down with math.floor to stepSize to guarantee ZERO LOT_SIZE filter rejections
            floored_qty = math.floor((sell_qty or 0.0) / step_size) * step_size

            if floored_qty <= 0:
                self._respond_json(200, {
                    "success": False,
                    "error": f"Insufficient {cfg['baseAsset']} balance on Binance to sell. (Available: {sell_qty or 0.0})"
                })
                return

            params["quantity"] = f"{floored_qty:.{decimals}f}"

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
        if err_code == -2015 or "permissions" in str(err_msg).lower():
            err_msg += " • (Fix: In your Binance API settings, check 'Enable Spot & Margin Trading'. If IP restriction is disabled, ensure key was saved with 2FA)."
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

    def handle_futures_connection(self, api_key, api_secret):
        timestamp = get_binance_server_time()
        query_string = f"timestamp={timestamp}&recvWindow=60000"
        signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

        for base_url in ["https://fapi.binance.com", "https://fapi1.binance.com"]:
            full_url = f"{base_url}/fapi/v2/balance?{query_string}&signature={signature}"
            req = urllib.request.Request(full_url, headers={
                'X-MBX-APIKEY': api_key,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            try:
                with urllib.request.urlopen(req, timeout=6) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    usdt_balance = 0.0
                    for item in res_data:
                        if item.get("asset") == "USDT":
                            usdt_balance = float(item.get("availableBalance", item.get("balance", 0.0)))
                            break
                    self._respond_json(200, {
                        "success": True,
                        "marketType": "FUTURES",
                        "usdtBalance": round(usdt_balance, 2),
                        "message": f"Binance USD-M Futures connected! Available USDT: ${usdt_balance:.2f}"
                    })
                    return
            except urllib.error.HTTPError as e:
                try:
                    err_data = json.loads(e.read().decode('utf-8'))
                    err_msg = err_data.get("msg", str(e))
                except Exception:
                    err_msg = str(e)
                self._respond_json(200, {
                    "success": False,
                    "error": f"Binance Futures error: {err_msg} (Ensure 'Enable Futures' is checked in your API Key settings)"
                })
                return
            except Exception as e:
                continue

        self._respond_json(200, {
            "success": False,
            "error": "Failed to connect to Binance Futures endpoint."
        })

    def handle_create_futures_order(self, api_key, api_secret, data):
        symbol = data.get("symbol", "BTCUSDT").upper()
        side = data.get("side", "BUY").upper()
        order_type = data.get("type", "MARKET").upper()
        quantity = data.get("quantity")
        leverage = int(data.get("leverage", 10))

        # 1. Set leverage on Binance USD-M
        ts = get_binance_server_time()
        lev_query = f"symbol={symbol}&leverage={leverage}&timestamp={ts}&recvWindow=60000"
        lev_sig = hmac.new(api_secret.encode('utf-8'), lev_query.encode('utf-8'), hashlib.sha256).hexdigest()
        try:
            lev_req = urllib.request.Request(f"https://fapi.binance.com/fapi/v1/leverage?{lev_query}&signature={lev_sig}", data=b"", headers={
                'X-MBX-APIKEY': api_key, 'User-Agent': 'Mozilla/5.0'
            }, method="POST")
            urllib.request.urlopen(lev_req, timeout=4)
        except Exception:
            pass

        # 2. Place Market Order
        ts2 = get_binance_server_time()
        cfg = SYMBOL_CONFIG.get(symbol, {"stepSize": 0.001, "decimals": 3, "baseAsset": symbol.replace("USDT","")})
        decimals = cfg["decimals"]
        step_size = cfg["stepSize"]

        # If quantity is not explicitly set, calculate minimal safe lot
        order_qty = None
        if quantity and str(quantity).upper() != "ALL":
            try:
                order_qty = float(quantity)
            except ValueError:
                order_qty = None

        if order_qty is None or order_qty <= 0:
            order_qty = step_size * 5

        floored_qty = math.floor(order_qty / step_size) * step_size
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": f"{floored_qty:.{decimals}f}",
            "timestamp": ts2,
            "recvWindow": 60000
        }
        q_str = urllib.parse.urlencode(params)
        sig = hmac.new(api_secret.encode('utf-8'), q_str.encode('utf-8'), hashlib.sha256).hexdigest()
        full_url = f"https://fapi.binance.com/fapi/v1/order?{q_str}&signature={sig}"

        try:
            req = urllib.request.Request(full_url, data=b"", headers={
                'X-MBX-APIKEY': api_key, 'User-Agent': 'Mozilla/5.0'
            }, method="POST")
            with urllib.request.urlopen(req, timeout=6) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                self._respond_json(200, {
                    "success": True,
                    "order": res_data,
                    "message": f"Binance Futures order executed: {side} {symbol} ({leverage}x)"
                })
        except urllib.error.HTTPError as e:
            try:
                err_data = json.loads(e.read().decode('utf-8'))
                err_msg = err_data.get("msg", str(e))
            except Exception:
                err_msg = str(e)
            self._respond_json(200, {
                "success": False,
                "error": f"Futures order rejected: {err_msg}"
            })
        except Exception as e:
            self._respond_json(200, {
                "success": False,
                "error": f"Futures execution error: {str(e)}"
            })
