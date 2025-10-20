# Delta Neutral Volume Generation Bot for Lighter DEX# Delta Neutral Volume Generation Bot for Lighter DEX# Delta Neutral Volume Generation Bot for Lighter DEX



A sophisticated trading bot that executes delta-neutral strategies on Lighter DEX by simultaneously opening long and short positions across two accounts. Generates genuine trading volume while maintaining market neutrality.



## 🎯 Key FeaturesA sophisticated trading bot that executes delta-neutral strategies on Lighter DEX by simultaneously opening long and short positions across two accounts. The bot automatically closes positions after a configurable delay, generating genuine trading volume while maintaining market neutrality.A sophisticated trading bot that executes delta-neutral strategies on Lighter DEX by simultaneously opening long and short positions across two accounts with equal notional value. This generates genuine trading volume while maintaining market neutrality.



- **Delta Neutral Strategy**: Simultaneous long/short orders with equal notional value

- **Multi-Market Support**: Random selection from whitelisted markets

- **Dynamic Leverage**: Optional randomized leverage per trade within market limits## 🎯 Key Features## 📚 Documentation

- **Automatic Position Management**: Opens and closes positions with randomized timing

- **Isolated Workers**: Separate processes for each account prevent signer conflicts

- **API-Based Precision**: Fetches official size_decimals from Lighter API for accurate order sizing

- **Comprehensive Logging**: Detailed execution logs for monitoring and debugging- **Delta Neutral Strategy**: Simultaneously executes long (buy) and short (sell) orders with identical notional amounts**📖 Complete documentation is available in the [`docs/`](docs/) folder.**



## 📋 Prerequisites- **Automatic Position Closing**: Closes positions after a random delay (30-50 seconds by default)



- **Python 3.12+** installed- **Configurable Leverage**: Set leverage and margin mode via environment variables (default: 10x cross margin)**New users should start with: [`docs/START_HERE.md`](docs/START_HERE.md)**

- **Two Lighter DEX accounts** with:

  - Private keys (including API keys)- **Dual Account Management**: Uses isolated worker processes to manage two separate accounts

  - Account indices

  - API key indices- **Market Order Execution**: Uses market orders with configurable slippage protectionKey documentation:

  - Sufficient balance for trading

- **Reduce-Only Closing**: Safely closes positions without risk of opening new ones- **[START_HERE.md](docs/START_HERE.md)** - Complete overview and quick reference

## 🚀 Quick Start

- **Continuous Operation**: Runs continuously with configurable intervals- **[FIRST_TIME_SETUP.md](docs/FIRST_TIME_SETUP.md)** - Step-by-step setup guide

### 1. Clone and Setup

- **Comprehensive Logging**: Detailed logs for monitoring and debugging- **[TESTNET_FUNDS_GUIDE.md](docs/TESTNET_FUNDS_GUIDE.md)** - ⚠️ CRITICAL: Testnet $500 budget management

```powershell

cd "e:\Volume Generation Bot"- **Native Windows Support**: Runs directly on Windows using Python virtual environment- **[PRE_LAUNCH_CHECKLIST.md](docs/PRE_LAUNCH_CHECKLIST.md)** - Pre-flight checklist



# Create virtual environment- **[QUICKSTART.md](docs/QUICKSTART.md)** - Quick command reference

python -m venv venv

## 📋 Prerequisites- **[docs/README.md](docs/README.md)** - Full documentation index

# Activate virtual environment

.\venv\Scripts\Activate.ps1



# Install dependencies- Python 3.12+ installed on Windows---

pip install -r requirements.txt

```- Two Lighter DEX accounts with:



### 2. Configure Environment  - Private keys## 🎯 Features



Copy `.env.example` to `.env` and configure:  - Account indices



```powershell  - API key indices- **Delta Neutral Strategy**: Simultaneously executes long (buy) and short (sell) orders with identical notional amounts

Copy-Item .env.example .env

notepad .env- Sufficient balance in both accounts for trading (testnet provides $500 per account)- **Dual Account Management**: Manages two separate accounts for long and short positions

```

- **Market Order Execution**: Uses market orders with configurable slippage protection

**Critical Settings:**

## 🚀 Quick Start- **Batch Transaction Support**: Optional batch mode for improved atomicity

```env

# Network- **Continuous Operation**: Runs continuously with configurable intervals

BASE_URL=https://mainnet.zklighter.elliot.ai

### 1. Set Up Python Environment- **Docker Support**: Fully containerized for easy deployment on any platform

# Accounts

ACCOUNT1_PRIVATE_KEY=0xYOUR_KEY_HERE- **Comprehensive Logging**: Detailed logs for monitoring and debugging

ACCOUNT1_INDEX=123456

ACCOUNT2_PRIVATE_KEY=0xYOUR_KEY_HERE```powershell- **Configurable Parameters**: All trading parameters configurable via environment variables

ACCOUNT2_INDEX=234567

# Create virtual environment

# Trading

MARKET_WHITELIST=0,1,2,3,7,9,24,25,27,35python -m venv venv## 📋 Prerequisites

BASE_AMOUNT_IN_USDT=2  # $2 margin per account

LEVERAGE=50

USE_DYNAMIC_LEVERAGE=true

```# Activate virtual environment- Docker and Docker Compose installed on your system



### 3. Check Balances.\venv\Scripts\Activate.ps1- Two Lighter DEX accounts with API keys



### Safety Floors

Set optional guard rails to halt trading if available balances fall too low:

```env
# Stop if Account 1 drops below $250
MIN_ACCOUNT1_BALANCE=250

# Stop if Account 2 drops below $250 (leave blank to disable)
MIN_ACCOUNT2_BALANCE=

# Or enforce a combined floor across both accounts
MIN_COMBINED_BALANCE=600

# Stop the session if realized bleed exceeds a negative loss cap (<= 0)
MAX_SESSION_BLEED=-100
```

All balance thresholds must be non-negative. `MAX_SESSION_BLEED` must be zero or negative because it represents an allowed loss. When triggered the bot logs a critical alert, stops opening new trades, and lets existing positions settle.

## 📲 Telegram Operations

Integrate the orchestrator with Telegram for real-time monitoring and operator commands.

### Environment Variables

Add the following settings to your `.env` file:

```env
# Telegram bot credentials
TELEGRAM_BOT_TOKEN=123456789:ABCDEF_your_botfather_token
TELEGRAM_OPERATOR_CHAT_ID=123456789  # comma-separated list supported via TELEGRAM_OPERATOR_CHAT_IDS

# Optional broadcast channel for automated trade logs
TELEGRAM_BROADCAST_CHAT_ID=-1001234567890
```

> **Tip:** Use [@userinfobot](https://t.me/userinfobot) or `/setlogchannel` (see below) to discover chat IDs. Channel IDs usually begin with `-100`.

### Running the Telegram service

Install dependencies and launch the bot runner:

```bash
pip install -r requirements.txt
python telegram_runner.py --auto-post  # or --no-auto-post to disable automatic trade logs
```

The runner enforces operator-only access and wires the notifier into `DeltaNeutralOrchestrator`. Auto-posting defaults to `True` when a broadcast channel is configured; override it at startup or via `/setlogchannel`.

### Available commands

From an authorized chat:

| Command | Description |
|---------|-------------|
| `/status` | Current orchestrator status (running flag, trade counters, stop reason). |
| `/balances` | Latest cached balances for both accounts (forces a refresh). |
| `/config` | Non-sensitive configuration summary (base URL, markets, leverage settings). |
| `/session` | Aggregate session metrics including market-level trade volumes and bleed. |
| `/setlogchannel [chat_id] [on|off]` | View or update the broadcast channel. Passing `off` clears the channel and disables auto-posting. |

Trade opens, closes, balance snapshots, and drawdown alerts are delivered to all operator chats. When auto-posting is enabled they are also mirrored to the configured broadcast channel.


```powershell- Sufficient balance in both accounts for trading

python check_balances.py

```# Install dependencies



### 4. Test Configurationpip install -r requirements.txt## 🚀 Quick Start



```powershell

# Test market whitelist

python test_market_whitelist.py# Install Lighter SDK### 1. Clone or Download the Project

```

pip install -e .\lighter-python

### 5. Run the Bot

``````bash

```powershell

python delta_neutral_orchestrator.pycd "e:\Volume Generation Bot"

```

### 2. Configure Environment Variables```

## ⚙️ Configuration Guide



### Trade Sizing

Copy `.env.example` to `.env` and configure your settings:### 2. Configure Environment Variables

**BASE_AMOUNT_IN_USDT** (Recommended):

```env

BASE_AMOUNT_IN_USDT=2  # $2 margin per account

``````powershellCopy the example environment file and edit it with your credentials:

- Represents **margin (collateral)** per account, NOT notional value

- Notional value = margin × leverageCopy-Item .env.example .env

- Example: $2 margin × 50x leverage = $100 notional per side

notepad .env```bash

**BASE_AMOUNT** (Alternative):

```env```cp .env.example .env

BASE_AMOUNT=100  # Units with precision (fetched from API)

``````

- Precision varies by asset (BTC: 5 decimals, ETH: 4 decimals, etc.)

- Bot automatically fetches correct precision from Lighter API**Critical Configuration Parameters:**



### Market SelectionEdit `.env` file with your account details:



```env```env

MARKET_WHITELIST=0,1,2,3,7,9,24,25,27,35

```# Network Configuration```env

Available markets:

- Market 0: ETH (Max 50x)BASE_URL=https://testnet.zklighter.elliot.ai  # Testnet (safe for testing)# Account 1 (Long positions)

- Market 1: BTC (Max 50x)

- Market 2: SOL (Max 25x)# BASE_URL=https://api.lighter.xyz             # Mainnet (uses real funds!)ACCOUNT1_PRIVATE_KEY=0xYOUR_ACCOUNT1_PRIVATE_KEY_HERE

- Market 3: DOGE (Max 10x)

- Market 7: XRP (Max 20x)ACCOUNT1_INDEX=1

- Market 9: AVAX (Max 10x)

- Market 24: HYPE (Max 20x)# Account 1 (Long Positions)ACCOUNT1_API_KEY_INDEX=0

- Market 25: BNB (Max 20x)

- Market 27: AAVE (Max 10x)ACCOUNT1_PRIVATE_KEY=0xyour_private_key_here

- Market 35: LTC (Max 10x)

ACCOUNT1_INDEX=16# Account 2 (Short positions)

### Leverage Configuration

ACCOUNT1_API_KEY_INDEX=3ACCOUNT2_PRIVATE_KEY=0xYOUR_ACCOUNT2_PRIVATE_KEY_HERE

**Fixed Leverage:**

```envACCOUNT2_INDEX=2

LEVERAGE=50

USE_DYNAMIC_LEVERAGE=false# Account 2 (Short Positions)ACCOUNT2_API_KEY_INDEX=0

```

ACCOUNT2_PRIVATE_KEY=0xyour_private_key_here

**Dynamic Leverage:**

```envACCOUNT2_INDEX=15# Trading Parameters

LEVERAGE=50  # Base value (not used in dynamic mode)

USE_DYNAMIC_LEVERAGE=trueACCOUNT2_API_KEY_INDEX=3MARKET_INDEX=0

LEVERAGE_BUFFER=5  # Range: (max-5) to max

```BASE_AMOUNT=100000

- Each trade randomly selects leverage within market limits

- Each account gets independent random leverage# Trading ParametersMAX_SLIPPAGE=0.02

- Example: BTC with 50x max → Range 45x-50x

BASE_AMOUNT=100              # 0.01 ETH (100 / 10000)INTERVAL_SECONDS=60

### Timing Configuration

MAX_SLIPPAGE=0.1            # 10% slippage protectionMAX_TRADES=0

```env

# Wait before opening new trade (after previous closes)MARKET_INDEX=0              # ETH-PERP market```

MIN_OPEN_DELAY=80

MAX_OPEN_DELAY=120



# Position hold time# Leverage Configuration### 3. Build and Run with Docker

MIN_CLOSE_DELAY=30

MAX_CLOSE_DELAY=50LEVERAGE=10                 # 10x leverage



# Number of trades (0 = unlimited)MARGIN_MODE=0              # 0=cross, 1=isolated```bash

MAX_TRADES=0

```# Build the Docker image



**Important**: `MIN_OPEN_DELAY` must be ≥ `MAX_CLOSE_DELAY + 30` to prevent overlapping trades.# Position Closingdocker-compose build



## 🔧 ArchitectureMIN_CLOSE_DELAY=30         # Minimum seconds before closing



### Multi-Process DesignMAX_CLOSE_DELAY=50         # Maximum seconds before closing# Start the bot



```docker-compose up -d

┌─────────────────────────────────────┐

│   Delta Neutral Orchestrator        │# Bot Operation

│   (Main Process)                    │

│                                     │INTERVAL_SECONDS=60        # Wait time between NEW trades# View logs

│   • Market selection                │

│   • Trade coordination              │MAX_TRADES=3              # Stop after N trades (0=unlimited)docker-compose logs -f

│   • Position lifecycle management   │

└──────────┬──────────────────────────┘```

           │

           ├───────────────┬──────────────────┐# Stop the bot

           │               │                  │

    ┌──────▼──────┐ ┌──────▼──────┐         │### 3. Run the Botdocker-compose down

    │  Account 1  │ │  Account 2  │         │

    │   Worker    │ │   Worker    │         │```

    │  (Process)  │ │  (Process)  │         │

    │             │ │             │         │```powershell

    │  • Long     │ │  • Short    │         │

    │  • Orders   │ │  • Orders   │         │# Activate virtual environment if not already active## ⚙️ Configuration

    └─────────────┘ └─────────────┘         │

                                             │.\venv\Scripts\Activate.ps1

                                    ┌────────▼────────┐

                                    │  Lighter DEX    │### Environment Variables

                                    │    Mainnet      │

                                    └─────────────────┘# Run the orchestrator

```

python delta_neutral_orchestrator.py| Variable | Description | Default | Required |

**Why Isolated Processes?**

- Prevents signer conflicts between accounts```|----------|-------------|---------|----------|

- Each worker has its own SignerClient instance

- No shared state between accounts| `BASE_URL` | Lighter API base URL | `https://testnet.zklighter.elliot.ai` | No |

- More reliable order execution

## 📁 Project Structure| `ACCOUNT1_PRIVATE_KEY` | Private key for Account 1 (Long) | - | Yes |

### Trading Flow

| `ACCOUNT1_INDEX` | Account index for Account 1 | - | Yes |

1. **Initialization**

   - Load configuration from `.env````| `ACCOUNT1_API_KEY_INDEX` | API key index for Account 1 | `0` | No |

   - Validate against Lighter API (leverage limits, market availability)

   - Set leverage on both accountsVolume Generation Bot/| `ACCOUNT2_PRIVATE_KEY` | Private key for Account 2 (Short) | - | Yes |



2. **Trade Execution**├── .env                              # Your configuration (do not commit!)| `ACCOUNT2_INDEX` | Account index for Account 2 | - | Yes |

   - Randomly select market from whitelist

   - Fetch current bid/ask prices├── .env.example                      # Configuration template| `ACCOUNT2_API_KEY_INDEX` | API key index for Account 2 | `0` | No |

   - Fetch official size_decimals for precision

   - Calculate base_amount from margin target├── .gitignore                        # Git ignore rules| `MARKET_INDEX` | Market to trade (0 = ETH-USD) | `0` | No |

   - Execute simultaneous long (Account 1) and short (Account 2) orders

   - Schedule position closing├── README.md                         # This file| `BASE_AMOUNT` | Base asset amount per trade | `100000` | No |



3. **Position Closing**├── requirements.txt                  # Python dependencies| `MAX_SLIPPAGE` | Maximum acceptable slippage | `0.02` (2%) | No |

   - Background task monitors scheduled close times

   - Closes positions with reduce_only flag├── config.py                         # Configuration management| `INTERVAL_SECONDS` | Time between trades | `60` | No |

   - Uses fresh market prices

├── account_worker.py                 # Isolated account worker process| `MAX_TRADES` | Maximum trades (0 = unlimited) | `0` | No |

4. **Repeat**

   - Wait random delay (MIN_OPEN_DELAY to MAX_OPEN_DELAY)├── delta_neutral_orchestrator.py    # Main orchestrator (RUN THIS)| `USE_BATCH_MODE` | Use batch transactions | `false` | No |

   - Execute next trade

├── lighter-python/                   # Lighter SDK

## 📊 How Precision Works

├── references/                       # Reference implementation code### Trading Parameters Explained

The bot uses **official precision** from Lighter's API:

└── venv/                            # Python virtual environment

```python

# Fetch size_decimals from order book details```- **BASE_AMOUNT**: Amount in base asset with precision. For ETH (4 decimals):

order_book_details = await order_api.order_book_details(market_id=market_id)

precision_decimals = detail.size_decimals  - **IMPORTANT**: Testnet provides only $500 per account!



# Calculate base_amount## 🔧 Architecture  - `1000` = 0.0001 ETH (~$0.20 at $2000/ETH) - Recommended for testing

precision_multiplier = 10 ** precision_decimals

base_amount = (margin * leverage / price) * precision_multiplier  - `5000` = 0.0005 ETH (~$1.00 at $2000/ETH) - Good balance (default)

```

The bot uses a **multi-process architecture** to avoid conflicts with the Lighter SDK's C library signer:  - `10000` = 0.001 ETH (~$2.00 at $2000/ETH) - Moderate

**Examples:**

- BTC (5 decimals): `base_amount=100000` = 1.00000 BTC  - `100000` = 0.01 ETH (~$20 at $2000/ETH) - ⚠️ Too large for testnet!

- ETH (4 decimals): `base_amount=10000` = 1.0000 ETH

- SOL (3 decimals): `base_amount=1000` = 1.000 SOL1. **Orchestrator** (`delta_neutral_orchestrator.py`):  - See TESTNET_FUNDS_GUIDE.md for detailed fund management



## 📝 Example Trade   - Manages overall trading flow



**Configuration:**   - Coordinates two isolated worker processes- **MAX_SLIPPAGE**: Maximum price deviation acceptable:

```env

BASE_AMOUNT_IN_USDT=2   - Schedules position opening and closing  - `0.01` = 1% slippage

LEVERAGE=50

MARKET_WHITELIST=1  # BTC   - Handles timing and delays  - `0.02` = 2% slippage (recommended)

```

  - `0.05` = 5% slippage

**Execution:**

```2. **Workers** (`account_worker.py`):

BTC Price: $107,000

Target Margin: $2 per account   - Each runs as a separate Python process- **INTERVAL_SECONDS**: Time to wait between trade executions:

Leverage: 50x

   - Manages a single SignerClient instance  - `60` = 1 minute (recommended for testing)

Calculation:

- Target notional: $2 × 50 = $100   - Executes orders for one account  - `300` = 5 minutes

- Asset amount: $100 / $107,000 = 0.00093 BTC

- Precision: 5 decimals (from API)   - Communicates via JSON stdin/stdout  - `3600` = 1 hour

- base_amount: 0.00093 × 100000 = 93



Result:

- Long: Buy 0.00093 BTC ($99.51)This architecture ensures that each account has its own isolated C library signer, preventing nonce conflicts.## 📊 How It Works

- Short: Sell 0.00093 BTC ($99.51)

- Total margin: $4 ($2 per account)

- Total exposure: ~$200

- Delta neutral: ✅## ⚙️ Configuration Details1. **Initialization**: Bot connects to both accounts and verifies connectivity

```

2. **Price Discovery**: Fetches current market price from order book

## 🛠️ Troubleshooting

### Leverage Settings3. **Simultaneous Execution**: 

### "Invalid nonce" errors

✅ Solved by multi-process architecture - each worker has isolated signer   - Account 1: Places market BUY order (long position)



### "Leverage exceeds maximum" error```env   - Account 2: Places market SELL order (short position)

- Check market's max leverage with `test_market_whitelist.py`

- Reduce `LEVERAGE` setting in `.env`LEVERAGE=10          # 1-20x leverage4. **Delta Neutral**: Both orders have identical notional value, maintaining market neutrality

- Enable `USE_DYNAMIC_LEVERAGE` to stay within limits

MARGIN_MODE=0        # 0=cross margin, 1=isolated margin5. **Repeat**: Waits for configured interval and repeats

### Positions not closing

- Check logs for error messages```

- Verify accounts have sufficient balance

- Positions may already be closed (check manually)### Example Trade Flow



### Wrong order sizesCross margin (0) shares margin across all positions. Isolated margin (1) limits risk to each position separately.

✅ Fixed - Bot now fetches official `size_decimals` from Lighter API

```

## 📁 Project Structure

### Position ClosingCurrent Price: $2,000

```

Volume Generation Bot/Base Amount: 0.1 ETH

├── delta_neutral_orchestrator.py  # Main bot orchestrator

├── account_worker.py              # Isolated account worker```envMax Slippage: 2%

├── config.py                      # Configuration management

├── check_balances.py              # Balance checker utilityMIN_CLOSE_DELAY=30   # Minimum seconds to hold position

├── test_market_whitelist.py      # Market validation tool

├── requirements.txt               # Python dependenciesMAX_CLOSE_DELAY=50   # Maximum seconds to hold positionAccount 1 (Long):  Buy  0.1 ETH at max price $2,040 (2% above)

├── .env                           # Your configuration (DO NOT COMMIT)

├── .env.example                   # Configuration template```Account 2 (Short): Sell 0.1 ETH at min price $1,960 (2% below)

├── .gitignore                     # Git ignore rules

├── README.md                      # This file

├── venv/                          # Python virtual environment

└── lighter-python/                # Lighter SDKThe bot picks a random delay in this range for each trade, creating natural variation in position hold times.Net Position: 0 ETH (delta neutral)

```

Volume Generated: ~$400 total

## ⚠️ Important Notes

### Trading Amount```

### Testnet vs Mainnet



**Always test on testnet first!**

```env## 🐳 Docker Commands

- **Testnet**: `https://testnet.zklighter.elliot.ai` (Test funds)

- **Mainnet**: `https://mainnet.zklighter.elliot.ai` (Real money!)BASE_AMOUNT=100      # Represents 0.01 ETH (100 / 10000)



The bot logs a warning when running on mainnet.```### Build and Run



### Account Safety```bash



- Each account uses separate private keysThe base amount is scaled by 10,000. So:# Build the image

- Account indices must be different

- API keys must correspond to correct accounts- 100 = 0.01 ETHdocker-compose build

- Never commit `.env` file to version control

- 1000 = 0.1 ETH

### Risk Management

- 10000 = 1 ETH# Start in detached mode

- Start with small `BASE_AMOUNT_IN_USDT` values

- Test with `MAX_TRADES=5` before unlimited runsdocker-compose up -d

- Monitor logs regularly

- Ensure sufficient balance in both accounts### Slippage Protection

- Use `check_balances.py` before running

# Start with logs

## 🔍 Monitoring

```envdocker-compose up

### Log Files

MAX_SLIPPAGE=0.1     # 10% maximum slippage

Logs are written to:

- Console (stdout)```# Rebuild and start

- `delta_neutral_bot.log` file

docker-compose up -d --build

### What to Monitor

This prevents orders from executing at prices too far from the mid-price. Market orders use the mid-price ± slippage as price limits.```

- **Success Rate**: Percentage of successful trades

- **Execution Prices**: Compare with expected prices

- **Position Lifecycle**: Open → Hold → Close timing

- **Error Messages**: Connection or execution errors## 📊 How It Works### Monitoring

- **Account Balances**: Ensure sufficient funds

```bash

### Market Statistics

1. **Leverage Update**: On startup, sets leverage to configured value on both accounts# View logs

When using multiple markets, bot displays statistics at end:

```2. **Trade Execution**:docker-compose logs -f

Market Statistics

================================================================   - Fetches current market price from order book

  Market 0 (ETH): 15/15 trades (100.0% success)

  Market 1 (BTC): 12/12 trades (100.0% success)   - Calculates price limits with slippage protection# View last 100 lines

  Market 2 (SOL): 8/8 trades (100.0% success)

```   - Simultaneously places long order (Account 1) and short order (Account 2)docker-compose logs --tail=100



## 🧪 Testing   - Records position details and scheduled close time



### Check Configuration3. **Position Closing**:# Check container status



```powershell   - Background task monitors scheduled close timesdocker-compose ps

# Validate market whitelist and leverage limits

python test_market_whitelist.py   - When time arrives, places reduce-only orders to close positions```

```

   - Uses fresh market prices for closing

### Check Balances

4. **Repeat**: Waits for configured interval, then executes next trade### Management

```powershell

# View available balance and open positions```bash

python check_balances.py

```## 🔍 Monitoring# Stop the bot



### Test Rundocker-compose down



```powershellThe bot provides detailed logging:

# Run with limited trades

MAX_TRADES=3 python delta_neutral_orchestrator.py# Stop and remove volumes

```

```docker-compose down -v

## 🔐 Security Best Practices

2025-10-17 22:32:52 - INFO - ============================================================

1. **Never commit `.env`** - Contains sensitive private keys

2. **Use separate keys** for production and testing2025-10-17 22:32:52 - INFO - Trade #1# Restart the bot

3. **Start with small amounts** to test

4. **Monitor regularly**, especially initially2025-10-17 22:32:52 - INFO - ============================================================docker-compose restart

5. **Set MAX_TRADES limit** when testing

6. **Use testnet first** before mainnet2025-10-17 22:32:52 - INFO - Executing delta neutral trade:



## 📜 License2025-10-17 22:32:52 - INFO -   Base amount: 0.0100# Execute command in container



This project is for educational purposes. Use at your own risk.2025-10-17 22:32:52 - INFO -   Current price: $3780.00docker-compose exec delta-neutral-bot python --version



## 🤝 Support2025-10-17 22:32:52 - INFO -   Long max price: $4158.00```



For issues or questions about:2025-10-17 22:32:52 - INFO -   Short min price: $3402.00

- **Lighter DEX**: Check [official documentation](https://docs.lighter.xyz/)

- **This Bot**: Review logs and configuration2025-10-17 22:32:58 - INFO - ✅ Long order (Account 1): TX 28bf0d3346d88285...### Debugging

- **Discord**: [Lighter Discord](https://discord.gg/lighter)

2025-10-17 22:32:58 - INFO - ✅ Short order (Account 2): TX b2db284a4d50dedd...```bash

---

2025-10-17 22:32:58 - INFO - ✅ Delta neutral trade executed successfully# Access container shell

## 📈 Advanced Features

2025-10-17 22:32:58 - INFO - 📅 Position will close in 48 secondsdocker-compose exec delta-neutral-bot /bin/bash

### Dynamic Leverage

2025-10-17 22:32:58 - INFO - Success rate: 1/1 (100.0%)

Each trade randomly selects leverage within market limits:

``````# View log file inside container

BTC Market (Max 50x, Buffer 5):

  Trade 1: Long 48x, Short 50xdocker-compose exec delta-neutral-bot cat delta_neutral_bot.log

  Trade 2: Long 45x, Short 47x

  Trade 3: Long 50x, Short 46x## ⚠️ Important Notes

```

# Copy logs to host

Benefits:

- Creates more natural trading patterns### Testnet vs Mainnetdocker cp lighter-delta-neutral-bot:/app/delta_neutral_bot.log ./logs/

- Varies position sizes

- Maintains delta neutrality```



### Asymmetric Leverage**Always test on testnet first!**



With dynamic mode, each account gets **independent** random leverage:## 📁 Project Structure

```

Trade Example:- **Testnet**: `https://testnet.zklighter.elliot.ai` - Uses test funds ($500 limit per account)

  Long Account:  $2 margin × 48x = $96 notional

  Short Account: $2 margin × 50x = $100 notional- **Mainnet**: `https://api.lighter.xyz` - Uses REAL money!```

  

  Total Margin: $4Volume Generation Bot/

  Total Exposure: $196

  Delta Neutral: ✅ (Both sides present, nearly equal)The bot logs a warning if running on mainnet.├── delta_neutral_bot.py    # Main bot logic

```

├── config.py                # Configuration management

### Market Whitelist Rotation

### Account Indices├── requirements.txt         # Python dependencies

Bot randomly selects markets for each trade:

```├── Dockerfile              # Docker image definition

Trade 1: BTC (Market 1)

Trade 2: SOL (Market 2)Each account has:├── docker-compose.yml      # Docker Compose configuration

Trade 3: ETH (Market 0)

Trade 4: BTC (Market 1)- **Private Key**: For signing transactions├── .env.example            # Example environment variables

...

```- **Account Index**: Your account number on Lighter (find in account settings)├── .env                    # Your environment variables (gitignored)



This distributes volume across multiple markets naturally.- **API Key Index**: Which API key to use (usually 3)├── logs/                   # Log files directory



---└── lighter-python/         # Lighter Python SDK



**⚠️ DISCLAIMER**: This bot involves financial transactions. Always test on testnet first. Never use more funds than you can afford to lose. The authors are not responsible for any financial losses.These must match correctly or transactions will fail.    ├── docs/               # API documentation



**🚀 Happy Trading!**    ├── examples/           # Example scripts


### Position Management    └── .others/            # SDK source code

```

The bot:

- Opens positions with configurable leverage## 🔒 Security Best Practices

- Holds positions for random delays (30-50s default)

- Closes positions with `reduce_only=True` to prevent accidental new positions1. **Never commit `.env` file** to version control

- Waits for all positions to close before exiting2. **Use separate API keys** for production and testing

3. **Start with small amounts** to test the bot

### Error Handling4. **Monitor the bot** regularly, especially initially

5. **Set MAX_TRADES limit** when testing

If an error occurs:6. **Use testnet first** before mainnet deployment

1. Check the terminal output for error messages

2. Verify your `.env` configuration## 🧪 Testing

3. Ensure both accounts have sufficient balance

4. Check that private keys match account indices### Test on Lighter Testnet



## 🛠️ Troubleshooting1. Get testnet accounts from Lighter

2. Fund both accounts with testnet tokens

### "Invalid nonce" errors3. Configure `.env` with testnet credentials

- This is solved by the multi-process architecture4. Set `BASE_URL=https://testnet.zklighter.elliot.ai`

- Each worker has its own isolated signer5. Start with small `BASE_AMOUNT`

6. Set `MAX_TRADES=5` for limited testing

### "Account not found" errors

- Verify ACCOUNT1_INDEX and ACCOUNT2_INDEX match your actual account indices### Example Test Configuration

- Check that private keys correspond to these accounts

```env

### Position closing failsBASE_URL=https://testnet.zklighter.elliot.ai

- The bot now uses `reduce_only=True` which is safeBASE_AMOUNT=10000          # 0.001 ETH for testing

- If closing still fails, the position may have already been closed manuallyMAX_SLIPPAGE=0.05          # 5% for testnet

INTERVAL_SECONDS=120       # 2 minutes

### SDK errorsMAX_TRADES=10              # Limit to 10 trades

- Ensure lighter-python is installed: `pip install -e .\lighter-python````

- Check that virtual environment is activated

## 📈 Monitoring and Logs

## 📝 License

### Log Files

This project is for educational and testing purposes. Use at your own risk.

- `delta_neutral_bot.log`: Main log file (inside container)

## 🤝 Contributing- Console output: Real-time logs via `docker-compose logs -f`



This bot is designed for the Lighter DEX testnet. Always test thoroughly before any mainnet use.### Log Locations



## 📞 Support```bash

# View logs in container

For issues or questions about Lighter DEX:docker-compose exec delta-neutral-bot cat delta_neutral_bot.log

- Discord: https://discord.gg/lighter

- Documentation: https://docs.lighter.xyz/# Copy logs to host

mkdir -p logs

---docker cp lighter-delta-neutral-bot:/app/delta_neutral_bot.log ./logs/

```

**⚠️ DISCLAIMER**: This bot involves financial transactions. Always test on testnet first. Never use more funds than you can afford to lose. The authors are not responsible for any financial losses.

### What to Monitor

- **Success Rate**: Percentage of successful trades
- **Execution Prices**: Compare with expected prices
- **Slippage**: Actual vs maximum allowed
- **Error Messages**: Connection or execution errors
- **Account Balances**: Ensure sufficient funds

## ❌ Troubleshooting

### Bot Won't Start

```bash
# Check logs
docker-compose logs

# Verify environment variables
docker-compose config

# Rebuild image
docker-compose build --no-cache
docker-compose up
```

### Connection Errors

- Verify `BASE_URL` is correct
- Check internet connectivity
- Ensure API keys are valid
- Verify account indices are correct

### Trade Execution Failures

- Check account balances
- Verify market is active
- Reduce `BASE_AMOUNT` if insufficient balance
- Increase `MAX_SLIPPAGE` if price moves too fast
- Check for rate limiting

### Docker Issues

```bash
# Remove all containers and images
docker-compose down -v
docker system prune -a

# Rebuild from scratch
docker-compose build --no-cache
docker-compose up
```

## 🛠️ Development

### Local Testing (without Docker)

**Note**: The Lighter SDK doesn't support Windows directly. Use Docker or WSL2.

```bash
# Install dependencies
pip install -r requirements.txt

# Install Lighter SDK
cd lighter-python/.others
pip install -e .
cd ../..

# Set environment variables
export ACCOUNT1_PRIVATE_KEY="..."
export ACCOUNT1_INDEX="1"
# ... (set all required variables)

# Run the bot
python delta_neutral_bot.py
```

### Using WSL2 on Windows

```bash
# In WSL2 terminal
cd /mnt/e/"Volume Generation Bot"
python delta_neutral_bot.py
```

## 📝 Advanced Configuration

### Batch Mode

Enable batch transactions for better atomicity:

```env
USE_BATCH_MODE=true
```

Note: Batch mode signs transactions before sending, allowing for better nonce management.

### Custom Market

Trade different markets by changing the market index:

```env
MARKET_INDEX=1  # Different market
```

Check Lighter documentation for available markets.

### Rate Limiting

Adjust interval to avoid rate limits:

```env
INTERVAL_SECONDS=300  # 5 minutes between trades
```

## 🤝 Support

For issues related to:
- **Lighter API**: Check official Lighter documentation
- **This Bot**: Review logs and configuration
- **Docker**: Ensure Docker is properly installed

### Spread Guard

- `MAX_SPREAD_PERCENT` sets the maximum allowed bid/ask spread (in percent) before a trade is skipped. The default of `0.1` blocks trades when the spread is wider than 0.1% to avoid executing in illiquid order books.

## ⚠️ Disclaimer

This bot is for educational and volume generation purposes. Use at your own risk:

- **No Guarantees**: Trading involves risk
- **Test First**: Always test on testnet
- **Monitor Closely**: Don't leave unattended
- **Check Regulations**: Ensure compliance with local laws

## 📜 License

This project is provided as-is for educational purposes.

---

**Happy Trading! 🚀**
