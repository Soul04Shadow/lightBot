<<<<<<< HEAD
import asyncio
import json
import logging
from exchanges.variational_exchange import VariationalExchange

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_live_trading():
    print("----------------------------------------------------------------")
    print("   VARIATIONAL BROWSER TRADING TEST ")
    print("----------------------------------------------------------------")
    
    # 1. Load Config
    try:
        with open('exchange_config.json', 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        print("Error: exchange_config.json not found.")
        return

    variational_config = config_data['exchanges']['variational']
    variational_config['headless'] = False  # MUST be False to see browser and connect wallet
    
    # Optional: Test Proxy (Set your proxy here for testing if needed)
    # variational_config['proxy'] = "http://user:pass@host:port"

    # 2. Initialize
    print("\n[1] Launching Browser...")
    exchange = VariationalExchange(variational_config)
    success = await exchange.initialize()
    if not success:
        print("Failed to init browser.")
        return

    # 3. Auto-detected Wallet Connection
    # The initializing step now includes _ensure_wallet_connected logic.
    # We just double check here.
    
    # 4. Check Balance (Verification of connection)
    print("\n[3] Reading Balance...")
    balance_before = await exchange.get_balance()
    print(f"    Balance: ${balance_before}")
    if balance_before == 0:
        print("    WARNING: Balance is 0 or Wallet not connected.")
        # If balance IS 0, we can prompt, but otherwise we proceed automatically
        # confirm = input("    Continue anyway? (y/n): ")
        # if confirm.lower() != 'y':
        #     await exchange.close()
        #     return

    # 5. Place BUY Order
    symbol = "BTC"
    size = 0.001 # Small test size
    print(f"\n[4] Placing MARKET BUY Order for {size} {symbol}...")
    
    try:
        # Note: We use the exchange's create_market_order method
        result = await exchange.create_market_order(symbol, 'buy', size)
        print(f"    Result: {result}")
    except Exception as e:
        print(f"    ERROR Placing Order: {e}")

    # 6. Wait / Observe
    print("\n[5] Waiting 10 seconds to observe position...")
    await asyncio.sleep(10)

    # 7. Place SELL Order (Close/Cancel effect)
    print(f"\n[6] Placing MARKET SELL Order (Closing) for {size} {symbol}...")
    try:
        result = await exchange.create_market_order(symbol, 'sell', size)
        print(f"    Result: {result}")
    except Exception as e:
        print(f"    ERROR Placing Order: {e}")

    # 8. Final Balance
    print("\n[7] Reading Final Balance...")
    balance_after = await exchange.get_balance()
    print(f"    Balance: ${balance_after}")
    print(f"    Change: ${balance_after - balance_before:.4f}")

    print("\nTest Complete. Closing in 5s...")
    await asyncio.sleep(5)
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_live_trading())
=======
import asyncio
import json
import logging
from exchanges.variational_exchange import VariationalExchange

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_live_trading():
    print("----------------------------------------------------------------")
    print("   VARIATIONAL BROWSER TRADING TEST ")
    print("----------------------------------------------------------------")
    
    # 1. Load Config
    try:
        with open('exchange_config.json', 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        print("Error: exchange_config.json not found.")
        return

    variational_config = config_data['exchanges']['variational']
    variational_config['headless'] = False  # MUST be False to see browser and connect wallet
    
    # 2. Initialize
    print("\n[1] Launching Browser...")
    exchange = VariationalExchange(variational_config)
    success = await exchange.initialize()
    if not success:
        print("Failed to init browser.")
        return

    # 3. Auto-detected Wallet Connection
    # The initializing step now includes _ensure_wallet_connected logic.
    # We just double check here.
    
    # 4. Check Balance (Verification of connection)
    print("\n[3] Reading Balance...")
    balance_before = await exchange.get_balance()
    print(f"    Balance: ${balance_before}")
    if balance_before == 0:
        print("    WARNING: Balance is 0 or Wallet not connected.")
        # If balance IS 0, we can prompt, but otherwise we proceed automatically
        # confirm = input("    Continue anyway? (y/n): ")
        # if confirm.lower() != 'y':
        #     await exchange.close()
        #     return

    # 5. Place BUY Order
    symbol = "BTC"
    size = 0.001 # Small test size
    print(f"\n[4] Placing MARKET BUY Order for {size} {symbol}...")
    
    try:
        # Note: We use the exchange's create_market_order method
        result = await exchange.create_market_order(symbol, 'buy', size)
        print(f"    Result: {result}")
    except Exception as e:
        print(f"    ERROR Placing Order: {e}")

    # 6. Wait / Observe
    print("\n[5] Waiting 10 seconds to observe position...")
    await asyncio.sleep(10)

    # 7. Place SELL Order (Close/Cancel effect)
    print(f"\n[6] Placing MARKET SELL Order (Closing) for {size} {symbol}...")
    try:
        result = await exchange.create_market_order(symbol, 'sell', size)
        print(f"    Result: {result}")
    except Exception as e:
        print(f"    ERROR Placing Order: {e}")

    # 8. Final Balance
    print("\n[7] Reading Final Balance...")
    balance_after = await exchange.get_balance()
    print(f"    Balance: ${balance_after}")
    print(f"    Change: ${balance_after - balance_before:.4f}")

    print("\nTest Complete. Closing in 5s...")
    await asyncio.sleep(5)
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_live_trading())
>>>>>>> 3387475cbc6223223b2d33e4cdd33ebd6da08cef
