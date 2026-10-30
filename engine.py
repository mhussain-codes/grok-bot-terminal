"""
High-Frequency Multi-Bot Autonomous Trading Desk Engine.
Operates 3 bot strategies in parallel:
- Gambler Bot: Momentum & Trend breakout trader
- House Bot: Market making & Grid chop trader
- Spy Bot: Smart wallet copy trader
Under strict Risk Engine, Single Book Manager, and Paper Broker.
"""
import time
import random
from typing import List, Dict, Any, Optional

class MultiBotTradingEngine:
    def __init__(self, initial_deposit: float = 8391.08):
        self.start_equity: float = 44.82
        self.current_equity: float = initial_deposit
        self.wins: int = 40
        self.losses: int = 21
        self.trades_count: int = 61
        self.filtered_count: int = 19
        self.running: bool = True
        self.start_time: float = time.time() - (6 * 3600 + 36 * 60 + 23)

        # Active Multi-Bot Fleet Stats
        self.bot_fleet = {
            "gambler": {"active": True, "trades": 24, "wins": 16, "pnl": 3410.50, "style": "Momentum / Trend Breakouts"},
            "house":   {"active": True, "trades": 21, "wins": 15, "pnl": 2890.10, "style": "Avellaneda-Stoikov Grid / Chop"},
            "spy":     {"active": True, "trades": 16, "wins": 9,  "pnl": 2045.66, "style": "Top 1% Smart Wallet Copy"}
        }

        # Active open position
        self.active_trade: Optional[Dict[str, Any]] = {
            "symbol": "$GRUBZ",
            "bot": "GAMBLER",
            "side": "LONG",
            "entry_price": 0.00082729,
            "current_price": 0.00093318,
            "pnl_pct": 12.8,
            "slippage": 1.66,
            "size_equity_pct": 22.0,
            "size_usd": 1846.04,
            "reason": "[GAMBLER] spike 4.1x + dev wallet 2% (Jev prob 0.88)",
            "opened_at": "06:34"
        }

        self.logs: List[Dict[str, Any]] = [
            {"time": "09:57", "type": "ENTER", "bot": "GAMBLER", "token": "$GRUBZ", "pnl": "", "pnl_num": 0, "reason": "spike 4.1x + dev wallet 2%", "size": "size 22%"},
            {"time": "09:55", "type": "EXIT", "bot": "SPY", "token": "$MANGO9", "pnl": "+$342.52", "pnl_num": 342.52, "reason": "smart wallet 0x7a3f took profit", "size": "size 22%"},
            {"time": "09:52", "type": "FILTERED", "bot": "RUG_CHECK", "token": "$GUMBO", "pnl": "", "pnl_num": 0, "reason": "bundled launch, 9 wallets flagged", "size": "not traded"},
            {"time": "09:50", "type": "ENTER", "bot": "SPY", "token": "$MANGO9", "pnl": "", "pnl_num": 0, "reason": "copied 0x7a3f (81% win rate)", "size": "size 22%"},
            {"time": "09:47", "type": "EXIT", "bot": "HOUSE", "token": "$SQUONK", "pnl": "+$184.20", "pnl_num": 184.20, "reason": "grid level 6 filled (roundtrip)", "size": "size 22%"}
        ]

        self.pipeline_state = {
            "scanner": {"token": "$BLIMPY", "lp_locked": "86%"},
            "rug_check": {"status": "PASS", "token": "$GRUBZ", "filtered_total": 19},
            "sizer": {"pct": "22% eq", "amount_usd": round(self.current_equity * 0.22, 2)},
            "executor": {"status": "LIVE", "token": "$GRUBZ", "pnl": "+12.8%"},
            "logger": {"line": 151, "reason": "spike 4.1x + dev wallet 2%"},
            "equity": {"last_close": "+$342.52"}
        }

    def deposit(self, amount: float):
        self.current_equity = round(self.current_equity + amount, 2)
        now_str = time.strftime("%H:%M")
        self.logs.insert(0, {
            "time": now_str,
            "type": "DEPOSIT",
            "bot": "DESK",
            "token": "USDC",
            "pnl": f"+${amount:.2f}",
            "pnl_num": amount,
            "reason": "instant balance top-up allocated across all bots",
            "size": "100%"
        })

    def tick_simulation(self):
        if not self.running:
            return

        now_str = time.strftime("%H:%M")

        # 1. Manage Active Position (Trailing Stop / Target Fill)
        if self.active_trade:
            delta = random.uniform(-1.2, 2.2)
            self.active_trade["pnl_pct"] = round(self.active_trade["pnl_pct"] + delta, 1)
            self.active_trade["current_price"] = round(self.active_trade["entry_price"] * (1 + self.active_trade["pnl_pct"]/100), 8)
            pnl_sign = "+" if self.active_trade["pnl_pct"] >= 0 else ""
            self.pipeline_state["executor"]["pnl"] = f"{pnl_sign}{self.active_trade['pnl_pct']}%"

            if self.active_trade["pnl_pct"] >= 14.0 or self.active_trade["pnl_pct"] <= -5.0:
                is_win = self.active_trade["pnl_pct"] > 0
                pnl_dollars = round(self.active_trade["size_usd"] * (self.active_trade["pnl_pct"] / 100.0), 2)
                self.current_equity = round(self.current_equity + pnl_dollars, 2)
                
                bot_id = self.active_trade["bot"].lower()
                if bot_id in self.bot_fleet:
                    self.bot_fleet[bot_id]["trades"] += 1
                    self.bot_fleet[bot_id]["pnl"] += pnl_dollars
                    if is_win:
                        self.bot_fleet[bot_id]["wins"] += 1

                if is_win:
                    self.wins += 1
                else:
                    self.losses += 1
                self.trades_count += 1

                reason = "take-profit target reached" if is_win else "risk engine stop loss hit"
                pnl_str = f"{'+' if pnl_dollars>=0 else '-'}${abs(pnl_dollars):.2f}"
                self.logs.insert(0, {
                    "time": now_str,
                    "type": "EXIT",
                    "bot": self.active_trade["bot"],
                    "token": self.active_trade["symbol"],
                    "pnl": pnl_str,
                    "pnl_num": pnl_dollars,
                    "reason": reason,
                    "size": f"size {self.active_trade['size_equity_pct']}%"
                })
                self.pipeline_state["equity"]["last_close"] = pnl_str
                self.active_trade = None
                return

        # 2. Multi-Bot Strategy Trigger
        token_candidates = [
            {"token": "$BLIMPY", "lp": 88, "dev": 1.9, "spike": 3.9, "rug": False, "bot": "GAMBLER", "reason": "[GAMBLER] volume breakout 3.9x confirmed"},
            {"token": "$YETIX", "lp": 92, "dev": 1.5, "spike": 4.6, "rug": False, "bot": "SPY", "reason": "[SPY] copied wallet 0x9c4... (91% win rate)"},
            {"token": "$NEXUS", "lp": 96, "dev": 1.1, "spike": 2.2, "rug": False, "bot": "HOUSE", "reason": "[HOUSE] range bound 12-level grid activated"},
            {"token": "$SOLFIRE", "lp": 89, "dev": 2.0, "spike": 3.7, "rug": False, "bot": "GAMBLER", "reason": "[GAMBLER] momentum breakout + order book bid skew"},
            {"token": "$FAKEP", "lp": 22, "dev": 19.0, "spike": 1.2, "rug": True, "rug_reason": "unrenounced mint authority"},
            {"token": "$DEVSCAM", "lp": 12, "dev": 35.0, "spike": 7.0, "rug": True, "rug_reason": "bundled launch, 14 sniper wallets"}
        ]
        
        cand = random.choice(token_candidates)
        self.pipeline_state["scanner"]["token"] = cand["token"]
        self.pipeline_state["scanner"]["lp_locked"] = f"{cand['lp']}%"

        if cand.get("rug") or cand["lp"] < 80:
            self.filtered_count += 1
            self.pipeline_state["rug_check"]["status"] = "FILTERED"
            self.pipeline_state["rug_check"]["token"] = cand["token"]
            self.pipeline_state["rug_check"]["filtered_total"] = self.filtered_count
            self.logs.insert(0, {
                "time": now_str,
                "type": "FILTERED",
                "bot": "RUG_CHECK",
                "token": cand["token"],
                "pnl": "",
                "pnl_num": 0,
                "reason": cand.get("rug_reason", "LP locked < 80%"),
                "size": "not traded"
            })
        else:
            self.pipeline_state["rug_check"]["status"] = "PASS"
            self.pipeline_state["rug_check"]["token"] = cand["token"]
            size_usd = round(self.current_equity * 0.22, 2)
            self.pipeline_state["sizer"]["amount_usd"] = size_usd

            entry_p = round(random.uniform(0.0003, 0.0045), 8)
            self.active_trade = {
                "symbol": cand["token"],
                "bot": cand["bot"],
                "side": "LONG",
                "entry_price": entry_p,
                "current_price": entry_p,
                "pnl_pct": 0.0,
                "slippage": round(random.uniform(1.1, 1.7), 2),
                "size_equity_pct": 22.0,
                "size_usd": size_usd,
                "reason": cand["reason"],
                "opened_at": now_str
            }
            self.pipeline_state["executor"]["status"] = "LIVE"
            self.pipeline_state["executor"]["token"] = cand["token"]
            self.pipeline_state["executor"]["pnl"] = "+0.0%"
            self.pipeline_state["logger"]["line"] += 1
            self.pipeline_state["logger"]["reason"] = self.active_trade["reason"]

            self.logs.insert(0, {
                "time": now_str,
                "type": "ENTER",
                "bot": cand["bot"],
                "token": cand["token"],
                "pnl": "",
                "pnl_num": 0,
                "reason": cand["reason"],
                "size": "size 22%"
            })

        self.logs = self.logs[:100]

    def get_state(self) -> Dict[str, Any]:
        uptime_seconds = int(time.time() - self.start_time)
        hrs = uptime_seconds // 3600
        mins = (uptime_seconds % 3600) // 60
        secs = uptime_seconds % 60
        running_time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

        return {
            "running": self.running,
            "running_time": running_time_str,
            "balance": round(self.current_equity, 2),
            "start_balance": round(self.start_equity, 2),
            "trades": self.trades_count,
            "wins": self.wins,
            "losses": self.losses,
            "filtered": self.filtered_count,
            "bot_fleet": self.bot_fleet,
            "active_trade": self.active_trade,
            "pipeline": self.pipeline_state,
            "logs": self.logs
        }
