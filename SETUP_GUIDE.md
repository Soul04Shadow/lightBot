# DeltaBot Ultimate Setup & User Guide

## ï¿½ï¿½ Overview
DeltaBot is a state-of-the-art trading automation tool designed for **Delta Neutral Strategies** (Vol Farming) and **Statistical Arbitrage** (Pair Trading).

### í¼Ÿ Key Features
*   **Dual-Exchange Support**: Works with Lighter DEX (API) and **Variational** (Browser Automation/Stealth).
*   **Stealth Account Pooling**: Rotates between multiple wallets to hide your trading footprint.
*   **Monk Strategy**: Smart BTC/ETH Pair Trading (Short high performer / Long low performer).
*   **Robust Telegram Control**: Full remote management via Telegram.
*   **Browser Session Persistence**: Connect wallet once, run forever.

---

## í³‹ Prerequisites
1.  **Python 3.12+**
2.  **Google Chrome** (Required for Variational Browser Mode)
3.  **Telegram Account** (For bot control)

---

## í» ï¸ Installation Guide

### 1. Environment Setup
```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate (Windows)
.\venv\Scripts\activate
# OR Activate (Linux/Mac)
# source venv/bin/activate

# 3. Install Dependencies
pip install -r requirements.txt
```

### 2. Browser Driver (Crucial for Variational)
Since Variational uses browser automation, you need to install the Playwright browsers.
```bash
playwright install
```

---

## âš™ï¸ Configuration

### 1. The `.env` File
Create a file named `.env` in the root folder. Copy this template:

```ini
# --- TELEGRAM CONTROL ---
TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrSTUvwxyz"
TELEGRAM_OPERATOR_CHAT_IDS="12345678,87654321" # Your Telegram User ID
TELEGRAM_BROADCAST_CHAT_ID="" # Optional Channel ID for logs

# --- STRATEGY SETTINGS ---
# Mode: 'delta_neutral' (Volume) or 'monk' (Pair Trading)
STRATEGY_MODE=delta_neutral
BASE_AMOUNT_IN_USDT=50.0
LEVERAGE=10
MAX_SLIPPAGE=0.01

# --- ACCOUNT POOL (Stealth Mode) ---
# Define as many accounts as you want. The bot rotates them.

# Account 1 (Variational Example)
ACCOUNT1_EXCHANGE_TYPE=variational
ACCOUNT1_PRIVATE_KEY=0x...
ACCOUNT1_BASE_URL=https://omni.variational.io/perpetual/BTC

# Account 2 (Lighter Example)
ACCOUNT2_EXCHANGE_TYPE=lighter
ACCOUNT2_PRIVATE_KEY=0x...
ACCOUNT2_INDEX=2
ACCOUNT2_API_KEY_INDEX=2

# Account 3 (Another Variational)
ACCOUNT3_EXCHANGE_TYPE=variational
ACCOUNT3_USER_DATA_DIR=./browser_profile/acc3
```


### 2. Variational Selectors (`exchange_config.json`)
The bot uses CSS selectors to click buttons. This file is pre-configured but check it if the website design changes.

---

## íº€ Running the Bot

### Step 1: Login to Variational (One-Time)
If using Variational, you must log in manually first to save the session.
```bash
python test_live_trade.py
```
1.  The browser will open.
2.  **Connect your Wallet** manually.
3.  Close the script.
*Your session is now saved in `browser_profile/`.*

### Step 2: Start the Commander
Run the main Telegram Runner. This starts the bot and the Telegram listener.

```bash
python telegram_runner.py
```


---

## í³± Telegram Command Reference

Message your bot these commands:

### í¾® Controls
*   `/start` - Wake up the bot manager.
*   `/status` - Show live stats (Running state, Strategy, PnL, Open Positions).
*   `/pause` - Stop opening new trades (waits for current positions to close).
*   `/resume` - Resume trading.
*   `/stop` - Fully stop and exit the program.
*   `/forceclose` - íº¨ **EMERGENCY**: Close all open positions immediately.

### âš™ï¸ Live Tuning (No Restart Needed)
*   `/setstrategy [monk|delta_neutral]` - Switch strategy instantly.
*   `/setleverage [1-125]` - Change leverage on all accounts.
*   `/setsize [amount]` - Change trade size (in USDT).
*   `/config` - View current settings.

### í³Š Monitoring
*   `/pnl` - View detailed Session Profit & Loss.
*   `/session` - View volume generation stats.
*   `/balances` - View wallet balances.
*   `/setlogchannel [id]` - Set broadcast channel for trade logs.

---

## í·  Strategy Guide

### 1. Delta Neutral (Volume Farming)
*   **Goal**: Generate volume to farm rewards (e.g., points).
*   **Logic**: Opens Long on Account A and Short on Account B simultaneously. Holds for ~30s, then closes both. Result is 0 market risk.

### 2. Monk Strategy (Pair Trading)
*   **Goal**: Profit from BTC vs ETH divergence.
*   **Logic**:
    *   If ETH pumps >2% vs BTC: Short ETH / Long BTC.
    *   If ETH dumps >2% vs BTC: Long ETH / Short BTC.

