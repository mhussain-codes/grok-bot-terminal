# Grok Bot Terminal — 24/7 AI Quant Trading Desk

Autonomous, multi-agent AI trading desk engineered for Binance Spot & Futures markets. Operates strictly under probabilistic quant policy, hard risk controls, and zero-delegation veto gates.

![Grok Bot Terminal Architecture](https://raw.githubusercontent.com/mhussain-codes/grok-bot-terminal/main/ui/preview.png)

---

## ⚡ Key Highlights

- **3 Autonomous Strategies Running Concurrently**:
  - ⚡ **The Gambler**: Momentum breakout & EMA ribbon crossover (`EMA 7 > EMA 21` + volume surge).
  - 🏛️ **The House**: Mean-reversion grid quoting & oversold RSI capitulation bounces (`RSI < 30`).
  - 👁️ **The Spy**: Orderbook whale absorption & institutional volume spikes (`> 2.0x`).
- **Strict Capital Preservation (2.5 : 1 Reward-to-Risk)**:
  - Takes profit at $+2.5\%$ to $+3.5\%$ (ATR-scaled).
  - Enforces tight stop-losses at $-1.0\%$ (ATR-scaled).
- **Flexible Capital Routing ($1 to $1,000+)**:
  - If Spot balance $\ge \$5.00$: Places live market orders on Binance.
  - If balance is micro ($1 to $4): Sizes micro trades using live real-time Binance ticks and orderbook depth.
- **Zero Secret Leak Guarantee**:
  - All sensitive exchange keys are read via environment variables.
  - `.env` files are strictly git-ignored and never committed.

---

## 🚀 Setup & Installation Guide

### 1. Clone the Repository
```bash
git clone https://github.com/mhussain-codes/grok-bot-terminal.git
cd grok-bot-terminal
```

### 2. Configure Environment Keys (`.env`)
Create a `.env` file in the root directory (this file is excluded from GitHub):
```bash
# Create your .env file
touch .env
```
Add your Binance trading credentials:
```env
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here
```
> **Security Requirement**: When creating your API key on Binance, **Disable Withdrawals** (Trading only: Enable Spot / Margin Trading).

### 3. Run the Desk Locally
No complex dependencies needed (runs with pure Python standard library):
```bash
python server.py
```
Open your browser and navigate to:
```
http://localhost:8888
```

---

## 🌐 Deploy to Vercel (1-Click)

The repository includes a zero-config `vercel.json` and a serverless API handler (`api/state.py`).

1. Fork or push this repository to your GitHub.
2. Go to [Vercel](https://vercel.com/new).
3. Select `grok-bot-terminal` and click **Deploy**.
4. *(Optional)* In Vercel Project Settings $\rightarrow$ Environment Variables, you can securely add `BINANCE_API_KEY` and `BINANCE_SECRET_KEY` if you want the cloud instance to query your live portfolio.

---

## 🛡️ Risk Engine Specifications

- **Single Open Position Gate**: Maximum of 1 active market position at any given second. No concurrent scanning while in a position.
- **Micro Sizing Cap**: Never risks more than $20\%$ to $50\%$ of account equity per trade.
- **Spread & Liquidity Guard**: Any pair with an orderbook spread $> 15$ bps is immediately vetoed.
