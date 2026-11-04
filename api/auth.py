"""
User Authentication & Session Database API for Grok Bot Terminal.
Stores user accounts, passwords, personal Binance API keys, and balances.
Supports unique username signups, isolated logins, and persistent key storage.
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Persistent JSON Database path
# On Vercel serverless, /tmp is writable; locally, BASE_DIR is writable
DB_PATH = Path("/tmp/users_db.json") if os.getenv("VERCEL") else (BASE_DIR / "users_db.json")

def load_db():
    if DB_PATH.exists():
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_db(data):
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print("DB save error:", e)
        return False

class handler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-MBX-APIKEY')

    def _respond_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    _send_cors = _send_cors_headers

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        # Health / status
        self._respond_json(200, {
            "status": "online",
            "service": "Grok Bot User Database",
            "timestamp": int(time.time() * 1000)
        })

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        
        try:
            data = json.loads(body)
        except Exception as e:
            self._respond_json(400, {"success": False, "error": "Invalid JSON: " + str(e)})
            return

        action = data.get("action", "").strip()
        db = load_db()

        # -------------------------------------------------------------
        # 1. SIGN UP (Unique username, simple password)
        # -------------------------------------------------------------
        if action == "signup":
            username = data.get("username", "").strip()
            password = data.get("password", "").strip()

            if not username or not password:
                self._respond_json(400, {
                    "success": False, 
                    "error": "Username aur Password dono likhna zaroori hain!"
                })
                return

            if len(username) < 2:
                self._respond_json(400, {
                    "success": False, 
                    "error": "Username kam az kam 2 characters ka hona chahiye!"
                })
                return

            key = username.lower()
            if key in db:
                self._respond_json(400, {
                    "success": False, 
                    "error": f"⚠️ Yeh username '{username}' pehle se mojood hai! Kisi aur ka same nahi ho sakta, please doosra naam chunein."
                })
                return

            new_user = {
                "username": username,
                "password": password,
                "apiKey": "",
                "apiSecret": "",
                "balance": 5.0,
                "startBalance": 5.0,
                "tradingMode": "DEMO",
                "created_at": int(time.time()),
                "updated_at": int(time.time())
            }
            db[key] = new_user
            save_db(db)

            self._respond_json(200, {
                "success": True,
                "user": new_user,
                "message": f"Welcome {username}! Aapka private trading account ban gaya hai."
            })

        # -------------------------------------------------------------
        # 2. LOGIN (Isolated account session)
        # -------------------------------------------------------------
        elif action == "login":
            username = data.get("username", "").strip()
            password = data.get("password", "").strip()

            if not username or not password:
                self._respond_json(400, {
                    "success": False, 
                    "error": "Please username aur password dono enter karein."
                })
                return

            key = username.lower()
            if key not in db:
                self._respond_json(404, {
                    "success": False, 
                    "error": f"⚠️ User '{username}' nahi mila! Pehle 'SIGN UP' par click karke naya account banayein."
                })
                return

            user = db[key]
            if user.get("password") != password:
                self._respond_json(401, {
                    "success": False, 
                    "error": "❌ Galat Password! Please apna sahi password daalein."
                })
                return

            self._respond_json(200, {
                "success": True,
                "user": user,
                "message": f"Welcome back, {user.get('username', username)}! Aapka account login ho chuka hai."
            })

        # -------------------------------------------------------------
        # 3. SAVE API KEYS (Persistent to user account)
        # -------------------------------------------------------------
        elif action == "save_keys":
            username = data.get("username", "").strip()
            api_key = data.get("apiKey", "").strip()
            api_secret = data.get("apiSecret", "").strip()
            balance = data.get("balance")
            trading_mode = data.get("tradingMode", "LIVE")

            if not username:
                self._respond_json(400, {"success": False, "error": "Username missing"})
                return

            key = username.lower()
            if key not in db:
                db[key] = {
                    "username": username,
                    "password": "",
                    "apiKey": api_key,
                    "apiSecret": api_secret,
                    "balance": float(balance) if balance is not None else 5.0,
                    "startBalance": float(balance) if balance is not None else 5.0,
                    "tradingMode": trading_mode,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time())
                }
            else:
                db[key]["apiKey"] = api_key
                db[key]["apiSecret"] = api_secret
                db[key]["tradingMode"] = trading_mode
                if balance is not None:
                    db[key]["balance"] = float(balance)
                db[key]["updated_at"] = int(time.time())

            save_db(db)
            self._respond_json(200, {
                "success": True,
                "user": db[key],
                "message": "Binance API keys aapke database account mein save ho gayi hain!"
            })

        # -------------------------------------------------------------
        # 4. CLEAR KEYS (Only when user explicitly requests it)
        # -------------------------------------------------------------
        elif action == "clear_keys":
            username = data.get("username", "").strip()
            key = username.lower()
            if key in db:
                db[key]["apiKey"] = ""
                db[key]["apiSecret"] = ""
                db[key]["tradingMode"] = "DEMO"
                db[key]["updated_at"] = int(time.time())
                save_db(db)

            self._respond_json(200, {
                "success": True,
                "message": "Aapki API keys manually delete kar di gayi hain."
            })

        # -------------------------------------------------------------
        # 5. GET USER PROFILE
        # -------------------------------------------------------------
        elif action == "get_user":
            username = data.get("username", "").strip()
            key = username.lower()
            if key in db:
                self._respond_json(200, {
                    "success": True,
                    "user": db[key]
                })
            else:
                self._respond_json(404, {
                    "success": False,
                    "error": "User record not found in database."
                })

        # -------------------------------------------------------------
        # 6. SYNC / BACKUP USER (Client-to-server hydration)
        # -------------------------------------------------------------
        elif action == "sync_user":
            user_payload = data.get("user", {})
            uname = user_payload.get("username", "").strip()
            if uname:
                key = uname.lower()
                if key not in db or (user_payload.get("updated_at", 0) > db[key].get("updated_at", 0)):
                    db[key] = user_payload
                    save_db(db)
            self._respond_json(200, {"success": True, "db_users": list(db.keys())})

        else:
            self._respond_json(400, {
                "success": False,
                "error": f"Unknown action: {action}"
            })
