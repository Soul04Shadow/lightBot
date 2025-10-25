# API Adapter System Documentation

## Overview

The bot now supports multiple DEX platforms through a modular adapter system. This allows you to run the same delta-neutral trading strategy on different exchanges by simply switching the adapter.

## Architecture

The adapter system consists of several key components:

### 1. **APIAdapterBase** (`api_adapter_base.py`)
Abstract base class defining the interface all DEX adapters must implement. This ensures consistency across different platforms.

**Key data structures:**
- `MarketInfo`: Standardized market information
- `OrderResult`: Standardized order execution results
- `AccountBalance`: Account balance information
- `Position`: Position information
- `OrderBookPrice`: Order book pricing data

### 2. **Adapter Implementations** (`adapters/`)
DEX-specific implementations of the `APIAdapterBase` interface.

**Available Adapters:**
- **LighterAdapter** (`lighter_adapter.py`): Fully implemented for Lighter DEX
- **ParadexAdapter** (`paradex_adapter.py`): Template/example for Paradex (to be implemented)

### 3. **AdapterFactory** (`adapter_factory.py`)
Factory pattern for creating and managing adapter instances.

**Features:**
- Adapter registration system
- Configuration validation
- Worker adapter creation for isolated processes

### 4. **MarketDataProvider** (`market_data_provider.py`)
Adapter-agnostic market data access with caching support.

### 5. **AdapterAccountWorker** (`adapter_account_worker.py`)
Updated worker process that uses adapters instead of direct API calls.

## Using the Adapter System

### Configuration

Add the `API_ADAPTER` setting to your `.env` file:

```env
# API Adapter Selection
API_ADAPTER=lighter  # Options: lighter, paradex, dydx, hyperliquid, etc.

# Rest of your configuration...
BASE_URL=https://testnet.zklighter.elliot.ai
ACCOUNT1_PRIVATE_KEY=0x...
# ... etc
```

**Default:** If not specified, defaults to `lighter` for backward compatibility.

### Switching DEX Platforms

To switch to a different DEX:

1. **Set the adapter name:**
   ```env
   API_ADAPTER=paradex
   ```

2. **Update the base URL:**
   ```env
   BASE_URL=https://api.testnet.paradex.trade
   ```

3. **Adjust adapter-specific settings** (if needed)

4. **Restart the bot**

That's it! The bot will now use the Paradex adapter instead of Lighter.

## Creating a New Adapter

To add support for a new DEX, follow these steps:

### Step 1: Create Adapter Class

Create a new file in the `adapters/` directory (e.g., `adapters/dydx_adapter.py`):

```python
from api_adapter_base import (
    APIAdapterBase,
    MarketInfo,
    OrderResult,
    AccountBalance,
    Position,
    OrderBookPrice,
)

class DydxAdapter(APIAdapterBase):
    """API adapter for dYdX"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize dYdX client"""
        # Implement using dYdX SDK
        pass
    
    async def get_market_info(self, market_id: int) -> MarketInfo:
        """Fetch market info from dYdX"""
        # Implement using dYdX API
        pass
    
    # ... implement all other abstract methods
```

### Step 2: Implement All Required Methods

You must implement these abstract methods:

**Market Data:**
- `get_market_info(market_id)` - Get market details
- `get_order_book_prices(market_id)` - Get current bid/ask
- `get_size_decimals(market_id)` - Get order size precision

**Account:**
- `get_account_balance(account_index)` - Get account balance
- `get_account_positions(account_index, market_id)` - Get positions

**Trading:**
- `update_leverage(market_id, leverage, margin_mode)` - Set leverage
- `create_market_order(...)` - Execute market order

**Configuration:**
- `get_adapter_name()` - Return adapter identifier
- `get_required_config_keys()` - List required env vars
- `validate_config(config)` - Validate configuration

**Optional:**
- `supports_batch_orders()` - Batch order capability
- `get_default_base_url()` - Default testnet URL
- `get_mainnet_base_url()` - Mainnet URL

### Step 3: Register the Adapter

Update `adapter_factory.py`:

```python
from adapters.dydx_adapter import DydxAdapter

class AdapterFactory:
    _adapters: Dict[str, Type[APIAdapterBase]] = {
        'lighter': LighterAdapter,
        'paradex': ParadexAdapter,
        'dydx': DydxAdapter,  # Add your adapter here
    }
```

### Step 4: Update the Adapters Package

Update `adapters/__init__.py`:

```python
from .lighter_adapter import LighterAdapter
from .paradex_adapter import ParadexAdapter
from .dydx_adapter import DydxAdapter

__all__ = ['LighterAdapter', 'ParadexAdapter', 'DydxAdapter']
```

### Step 5: Test Your Adapter

Create tests for your adapter in `tests/test_<name>_adapter.py`:

```python
import pytest
from adapters.dydx_adapter import DydxAdapter

def test_dydx_adapter_initialization():
    config = {
        'base_url': 'https://api.dydx.exchange',
        'private_key': '0x...',
        'account_address': '0x...',
    }
    adapter = DydxAdapter(config)
    assert adapter.get_adapter_name() == 'dydx'
```

## Adapter-Specific Configuration

Different DEXes may require different configuration parameters:

### Lighter DEX
```env
API_ADAPTER=lighter
BASE_URL=https://testnet.zklighter.elliot.ai
ACCOUNT1_INDEX=123456
ACCOUNT1_API_KEY_INDEX=0
```

### Paradex (Example)
```env
API_ADAPTER=paradex
BASE_URL=https://api.testnet.paradex.trade
ACCOUNT1_ADDRESS=0x1234...  # Uses addresses instead of indices
ACCOUNT1_API_KEY=your_api_key
```

### dYdX (Example)
```env
API_ADAPTER=dydx
BASE_URL=https://api.dydx.exchange
ACCOUNT1_ADDRESS=0x1234...
ACCOUNT1_STARK_PRIVATE_KEY=0x...  # May need different key types
```

## Migration Guide

### From Old Code (Lighter-only)

**Old approach:**
```python
import lighter
client = lighter.SignerClient(url=url, private_key=pk, ...)
```

**New approach:**
```python
from adapter_factory import AdapterFactory

adapter = AdapterFactory.create_adapter('lighter', config)
await adapter.initialize()
```

### Benefits of the New System

1. **Platform Independence**: Same bot logic works across multiple DEXes
2. **Easy Testing**: Mock adapters for unit testing
3. **Future-Proof**: Add new platforms without changing core logic
4. **Consistent Interface**: All DEXes accessed through same API
5. **Better Isolation**: Adapter bugs don't affect core trading logic

## Advanced Usage

### Using Multiple Adapters

You can run different strategies on different DEXes simultaneously by creating multiple bot instances with different configurations.

### Custom Market Data Providers

Create custom data providers for specialized use cases:

```python
from market_data_provider import MarketDataProvider

provider = MarketDataProvider(
    adapter=my_adapter,
    cache_ttl_seconds=600  # Custom cache duration
)

market_info = await provider.get_market_info(market_id=0)
```

### Adapter Manager

For complex scenarios with multiple accounts across different DEXes:

```python
from adapter_factory import AdapterManager

manager = AdapterManager(adapter_name='lighter')
manager.create_account_adapter('account1', account1_config)
manager.create_account_adapter('account2', account2_config)

await manager.initialize_all()
```

## Troubleshooting

### "Unknown adapter" error
- Check that your adapter is registered in `adapter_factory.py`
- Verify the `API_ADAPTER` value in your `.env` file

### "Missing required config key" error
- Check `get_required_config_keys()` in your adapter
- Ensure all required environment variables are set

### Import errors
- Ensure the adapter's dependencies are installed
- Check that adapter files are in the `adapters/` directory

### Initialization failures
- Verify API credentials are correct
- Check network connectivity
- Review adapter-specific logs

## Best Practices

1. **Always validate configuration** in `validate_config()`
2. **Handle API errors gracefully** with proper error messages
3. **Cache market data** to reduce API calls
4. **Log important operations** for debugging
5. **Test with testnet first** before using real funds
6. **Document adapter-specific quirks** in code comments
7. **Keep adapters focused** on API translation, not business logic

## Contributing New Adapters

We welcome community contributions of new DEX adapters!

**Before implementing:**
1. Check if the DEX has a Python SDK
2. Verify it supports perpetual futures/margin trading
3. Ensure it has reliable APIs for order execution

**When submitting:**
1. Include comprehensive tests
2. Document any DEX-specific requirements
3. Provide example configuration
4. Add error handling for edge cases

## Future Enhancements

Planned improvements to the adapter system:

- [ ] WebSocket support for real-time data
- [ ] Batch order execution interface
- [ ] Rate limiting middleware
- [ ] Adapter health monitoring
- [ ] Auto-retry mechanisms
- [ ] Performance metrics per adapter
- [ ] Adapter versioning system

## Support

For help with the adapter system:
- Check existing adapter implementations as examples
- Review the `ParadexAdapter` template
- See test files for usage patterns
- File issues on GitHub for bugs or questions
