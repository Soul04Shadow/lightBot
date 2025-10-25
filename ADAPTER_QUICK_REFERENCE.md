# Quick Reference: Using the Adapter System

## Switch DEX Platform (3 Steps)

1. **Set adapter name** in `.env`:
   ```env
   API_ADAPTER=lighter  # or paradex, dydx, etc.
   ```

2. **Update base URL**:
   ```env
   BASE_URL=https://testnet.zklighter.elliot.ai
   ```

3. **Adjust account config** (if needed for platform)

## Available Adapters

| Adapter | Status | Testnet URL | Notes |
|---------|--------|-------------|-------|
| `lighter` | ✅ Ready | `https://testnet.zklighter.elliot.ai` | Default, fully implemented |
| `paradex` | 🚧 Template | `https://api.testnet.paradex.trade` | Example/template only |
| `dydx` | ⏳ Planned | TBD | Not yet implemented |

## Common Tasks

### Get Available Adapters
```python
from adapter_factory import AdapterFactory
print(AdapterFactory.get_available_adapters())
# Output: ['lighter', 'paradex']
```

### Create an Adapter
```python
from adapter_factory import AdapterFactory

config = {
    'base_url': 'https://testnet.zklighter.elliot.ai',
    'private_key': '0x...',
    'account_index': 123456,
}

adapter = AdapterFactory.create_adapter('lighter', config)
await adapter.initialize()
```

### Use Market Data Provider
```python
from market_data_provider import MarketDataProvider

provider = MarketDataProvider(adapter, cache_ttl_seconds=300)

# Get market info (cached)
info = await provider.get_market_info(market_id=0)
print(f"Market: {info.symbol}, Max Leverage: {info.max_leverage}x")

# Get current prices
prices = await provider.get_order_book_prices(market_id=0)
print(f"Bid: ${prices.best_bid}, Ask: ${prices.best_ask}")
```

### Check Account Balance
```python
balance = await adapter.get_account_balance(account_index=123456)
print(f"Available: ${balance.available_balance:.2f}")
```

### Execute an Order
```python
result = await adapter.create_market_order(
    market_id=0,
    base_amount=1000,
    is_ask=False,  # Buy/Long
    execution_price=3000_000000,
    reduce_only=False
)

if result.success:
    print(f"Order executed: {result.tx_hash}")
else:
    print(f"Order failed: {result.error}")
```

## Create New Adapter (Quick Steps)

1. **Copy template**: `cp adapters/paradex_adapter.py adapters/my_dex_adapter.py`
2. **Rename class**: `class MyDexAdapter(APIAdapterBase):`
3. **Implement methods**: Replace TODO comments with actual API calls
4. **Register**: Add to `adapter_factory.py`
5. **Test**: Create tests and verify functionality

## Environment Variables

### Required (All Adapters)
```env
API_ADAPTER=lighter
BASE_URL=https://...
```

### Lighter-Specific
```env
ACCOUNT1_INDEX=123456
ACCOUNT1_API_KEY_INDEX=0
```

### Paradex-Specific (Example)
```env
ACCOUNT1_ADDRESS=0x...
ACCOUNT1_API_KEY=abc123
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| "Unknown adapter" | Check `API_ADAPTER` value matches registered name |
| "Missing config key" | Add required fields for your adapter |
| "Not implemented" | Adapter method needs implementation |
| Import error | Check adapter files are in `adapters/` directory |

## File Locations

```
api_adapter_base.py          # Base interface
adapter_factory.py           # Factory & manager
market_data_provider.py      # Market data access
adapter_account_worker.py    # Worker process

adapters/
  lighter_adapter.py         # Lighter implementation
  paradex_adapter.py         # Template/example
  your_adapter.py            # Add custom adapters here

docs/
  API_ADAPTER_GUIDE.md       # Full documentation
  MIGRATION_GUIDE.md         # Migration help
```

## Key Data Structures

```python
@dataclass
class MarketInfo:
    market_id: int
    symbol: str
    max_leverage: int
    price_decimals: int
    size_decimals: int

@dataclass
class OrderResult:
    success: bool
    tx_hash: Optional[str]
    error: Optional[str]

@dataclass  
class AccountBalance:
    available_balance: float
    total_balance: float
    margin_used: Optional[float]

@dataclass
class OrderBookPrice:
    best_bid: Optional[float]
    best_ask: Optional[float]
    mid_price: Optional[float]
```

## Important Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_market_info(market_id)` | Market details | `MarketInfo` |
| `get_order_book_prices(market_id)` | Current prices | `OrderBookPrice` |
| `get_account_balance(account_index)` | Balance info | `AccountBalance` |
| `update_leverage(...)` | Set leverage | `(bool, str)` |
| `create_market_order(...)` | Execute order | `OrderResult` |

## Testing

```bash
# Test adapter creation
python -c "from adapter_factory import AdapterFactory; print(AdapterFactory.get_available_adapters())"

# Test with existing scripts
python check_balances.py
python test_market_whitelist.py

# Run unit tests
pytest tests/test_lighter_adapter.py
```

## Need Help?

- 📖 Full Guide: [docs/API_ADAPTER_GUIDE.md](docs/API_ADAPTER_GUIDE.md)
- 🔄 Migration: [docs/MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md)
- 📝 Summary: [ADAPTER_IMPLEMENTATION_SUMMARY.md](ADAPTER_IMPLEMENTATION_SUMMARY.md)
- 💡 Examples: Check `adapters/lighter_adapter.py` for working code

## Quick Commands

```bash
# Check current adapter
grep API_ADAPTER .env

# List adapter files
ls -la adapters/*.py

# View adapter info
python -c "from adapters.lighter_adapter import LighterAdapter; a = LighterAdapter({}); print(a.get_adapter_name())"

# Test adapter factory
python -c "from adapter_factory import AdapterFactory; print('Available:', AdapterFactory.get_available_adapters())"
```
