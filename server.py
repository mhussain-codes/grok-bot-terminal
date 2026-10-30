"""
Server for Grok Bot Terminal.
Runs background autonomous agent loop and serves UI on port 8888.
"""
import os
import json
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
from pathlib import Path
from quant_engine import ProfessionalQuantEngine

api_key = os.getenv("OKX_API_KEY", "")
secret_key = os.getenv("OKX_SECRET_KEY", "")
passphrase = os.getenv("OKX_PASSPHRASE", "")

engine = ProfessionalQuantEngine(api_key, secret_key, passphrase)

def background_trading_loop():
    while True:
        try:
            engine.tick()
        except Exception as e:
            print("Engine error:", e)
        time.sleep(1.0)  # Real-time 1-second cadence

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
            # Serve UI index.html
            html_file = BASE_DIR / "ui" / "index.html"
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
            amount = float(data.get("amount", 100.0))
            engine.deposit(amount)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "balance": engine.current_equity}).encode("utf-8"))

def start():
    port = 8888
    server = HTTPServer(("", port), DeskHandler)
    print(f"Grok Bot Terminal running on http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    start()
