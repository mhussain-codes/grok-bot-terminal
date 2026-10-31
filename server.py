"""
Server for Grok Bot Terminal - Powered by Binance Quant Engine.
Zero hardcoded keys: reads exclusively from environment variables or .env.local.
"""
import os
import json
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
from pathlib import Path
from binance_engine import BinanceTradingEngine

# Read keys strictly from Environment Variables (Zero Secrets in code)
api_key = os.getenv("BINANCE_API_KEY", "")
secret_key = os.getenv("BINANCE_SECRET_KEY", "")

# Load from local .env if present locally
env_file = Path(__file__).resolve().parent / ".env"
if env_file.exists():
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k == "BINANCE_API_KEY" and not api_key:
                    api_key = v.strip()
                elif k == "BINANCE_SECRET_KEY" and not secret_key:
                    secret_key = v.strip()

engine = BinanceTradingEngine(api_key, secret_key)

def background_trading_loop():
    while True:
        try:
            engine.tick()
        except Exception as e:
            print("Engine error:", e)
        time.sleep(1.0)

sim_thread = threading.Thread(target=background_trading_loop, daemon=True)
sim_thread.start()

BASE_DIR = Path(__file__).resolve().parent

class DeskHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/state":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(engine.get_state()).encode("utf-8"))
        elif parsed.path == "/api/toggle":
            engine.running = not engine.running
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"running": engine.running}).encode("utf-8"))
        else:
            html_file = BASE_DIR / "index.html"
            if html_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html_file.read_bytes())
            else:
                self.send_response(404)
                self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/deposit":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8")
            data = json.loads(raw) if raw else {}
            amount = float(data.get("amount", 5.0))
            if amount > 1000.0:
                amount = 1000.0
            engine.deposit(amount)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "balance": engine.current_equity}).encode("utf-8"))

def start(port=8888):
    server = HTTPServer(("", port), DeskHandler)
    print(f"Grok Bot Terminal running live on port {port}")
    server.serve_forever()

if __name__ == "__main__":
    start()
