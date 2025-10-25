# Testing Guide for API Adapter System

## Overview

This guide explains how to test the new API adapter system to ensure everything works correctly.

## Test Structure

```
tests/
├── test_adapter_base.py          # Base interface tests
├── test_adapter_factory.py       # Factory & manager tests
├── test_lighter_adapter.py       # Lighter adapter tests
├── test_market_data_provider.py  # Data provider tests
└── test_integration.py           # Integration tests (real API)

run_adapter_tests.py              # Test runner script
```

## Prerequisites

### Install Test Dependencies

```powershell
# Install pytest and related packages
pip install pytest pytest-asyncio pytest-cov

# Or install from requirements
pip install -r requirements.txt
```

### Setup for Integration Tests

Integration tests require real API credentials. Add to your `.env`:

```env
BASE_URL=https://testnet.zklighter.elliot.ai
ACCOUNT1_PRIVATE_KEY=0x...
ACCOUNT1_INDEX=123456
ACCOUNT1_API_KEY_INDEX=0
```

## Running Tests

### Quick Test (Recommended)

Run unit tests only (no API calls):

```powershell
python run_adapter_tests.py quick
```

Or using pytest directly:

```powershell
pytest tests/ -m "not integration"
```

### Unit Tests Only

Test all components without making API calls:

```powershell
python run_adapter_tests.py unit
```

Individual test files:

```powershell
# Test base interface
pytest tests/test_adapter_base.py -v

# Test factory
pytest tests/test_adapter_factory.py -v

# Test Lighter adapter
pytest tests/test_lighter_adapter.py -v

# Test market data provider
pytest tests/test_market_data_provider.py -v
```

### Integration Tests

⚠️ **WARNING**: These make REAL API calls to testnet!

```powershell
python run_adapter_tests.py integration
```

Or using pytest:

```powershell
pytest tests/test_integration.py -m integration -v
```

### All Tests

Run everything (unit + integration):

```powershell
python run_adapter_tests.py all
```

### With Coverage

Generate coverage report:

```powershell
python run_adapter_tests.py unit --coverage
```

Or using pytest-cov:

```powershell
pytest tests/ --cov=. --cov-report=html --cov-report=term
```

View coverage report:

```powershell
# Open in browser
start htmlcov/index.html
```

## Test Categories

### 1. Base Interface Tests (`test_adapter_base.py`)

**What it tests:**
- Data structure creation (MarketInfo, OrderResult, etc.)
- Abstract base class cannot be instantiated
- Subclasses must implement all required methods
- Helper methods have correct defaults

**Run:**
```powershell
pytest tests/test_adapter_base.py -v
```

**Key tests:**
- `test_market_info_creation` - MarketInfo dataclass works
- `test_order_result_success` - Order success handling
- `test_cannot_instantiate_abstract_class` - Abstract enforcement
- `test_complete_adapter_can_be_instantiated` - Valid implementation

### 2. Factory Tests (`test_adapter_factory.py`)

**What it tests:**
- Adapter creation and registration
- Configuration validation
- Adapter manager functionality
- Multiple adapter instances

**Run:**
```powershell
pytest tests/test_adapter_factory.py -v
```

**Key tests:**
- `test_get_available_adapters` - Lists registered adapters
- `test_create_lighter_adapter` - Creates Lighter instance
- `test_create_unknown_adapter_raises_error` - Error handling
- `test_adapter_manager` - Multi-account management

### 3. Lighter Adapter Tests (`test_lighter_adapter.py`)

**What it tests:**
- Lighter-specific configuration
- Config validation rules
- Required fields
- Default URLs

**Run:**
```powershell
pytest tests/test_lighter_adapter.py -v
```

**Key tests:**
- `test_adapter_name` - Returns 'lighter'
- `test_validate_valid_config` - Accepts valid config
- `test_validate_private_key_without_0x_prefix` - Rejects invalid keys
- `test_get_default_url` - Returns testnet URL

### 4. Market Data Provider Tests (`test_market_data_provider.py`)

**What it tests:**
- Caching functionality
- Cache expiration
- Cache bypass
- Statistics tracking

**Run:**
```powershell
pytest tests/test_market_data_provider.py -v
```

**Key tests:**
- `test_cache_market_info` - Data is cached
- `test_cache_expiration` - Cache expires after TTL
- `test_cache_bypass` - Can force refresh
- `test_clear_cache_specific_market` - Selective clearing

### 5. Integration Tests (`test_integration.py`)

**What it tests:**
- Real API calls to Lighter testnet
- Actual data fetching
- End-to-end workflows
- Performance with caching

**Run:**
```powershell
pytest tests/test_integration.py -m integration -v
```

**Key tests:**
- `test_get_market_info_eth` - Fetch ETH market data
- `test_get_order_book_prices` - Fetch real prices
- `test_get_account_balance` - Fetch account balance
- `test_full_workflow` - Complete usage scenario

## Manual Testing

### Test Adapter Creation

```powershell
python -c "
from adapter_factory import AdapterFactory

# List available adapters
print('Available:', AdapterFactory.get_available_adapters())

# Create Lighter adapter
config = {
    'base_url': 'https://testnet.zklighter.elliot.ai',
    'private_key': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
    'account_index': 1,
}
adapter = AdapterFactory.create_adapter('lighter', config)
print('Created:', adapter.get_adapter_name())
"
```

### Test Market Data Provider

```powershell
python -c "
import asyncio
from adapter_factory import AdapterFactory
from market_data_provider import MarketDataProvider

async def test():
    config = {
        'base_url': 'https://testnet.zklighter.elliot.ai',
        'private_key': '0x1234...your_key',
        'account_index': 123456,
    }
    
    adapter = AdapterFactory.create_adapter('lighter', config)
    await adapter.initialize()
    
    provider = MarketDataProvider(adapter, cache_ttl_seconds=60)
    
    # Fetch market info
    info = await provider.get_market_info(0)
    print(f'Market: {info.symbol}, Max Leverage: {info.max_leverage}x')
    
    # Check cache stats
    stats = provider.get_cache_stats()
    print(f'Cache stats: {stats}')
    
    await adapter.close()

asyncio.run(test())
"
```

### Test With Existing Scripts

Your existing scripts should work with the adapter system:

```powershell
# Test balance checking (ensure BASE_URL and credentials are in .env)
python check_balances.py

# Test market whitelist
python test_market_whitelist.py
```

## Continuous Testing

### Watch Mode (Auto-run on changes)

Install pytest-watch:

```powershell
pip install pytest-watch
```

Run in watch mode:

```powershell
ptw tests/ --runner "pytest -v"
```

### Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/sh
# Run unit tests before commit
python run_adapter_tests.py unit
```

Make it executable:

```powershell
chmod +x .git/hooks/pre-commit
```

## Troubleshooting

### Import Errors

**Problem:** `ImportError: cannot import name 'AdapterFactory'`

**Solution:**
```powershell
# Ensure you're in the project directory
cd "e:\Volume Generation Bot Paradex"

# Check files exist
ls api_adapter_base.py adapter_factory.py

# Add current directory to Python path if needed
$env:PYTHONPATH = "."
```

### Pytest Not Found

**Problem:** `pytest: command not found`

**Solution:**
```powershell
# Install pytest
pip install pytest pytest-asyncio

# Or use python -m pytest
python -m pytest tests/
```

### Integration Tests Failing

**Problem:** Integration tests fail with auth errors

**Solution:**
```powershell
# Check .env file has credentials
cat .env | Select-String "ACCOUNT1_PRIVATE_KEY"
cat .env | Select-String "ACCOUNT1_INDEX"

# Test credentials
python check_balances.py
```

### Async Test Warnings

**Problem:** `RuntimeWarning: coroutine was never awaited`

**Solution:**
```powershell
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Mark async tests with @pytest.mark.asyncio
```

## Expected Results

### Successful Unit Test Run

```
======================== test session starts =========================
tests/test_adapter_base.py::TestDataStructures::test_market_info_creation PASSED
tests/test_adapter_base.py::TestDataStructures::test_order_result_success PASSED
tests/test_adapter_factory.py::TestAdapterFactory::test_create_lighter_adapter PASSED
tests/test_lighter_adapter.py::TestLighterAdapterConfiguration::test_adapter_name PASSED
tests/test_market_data_provider.py::TestMarketDataProviderCaching::test_cache_market_info PASSED

======================== 20 passed in 0.45s ==========================
```

### Successful Integration Test Run

```
======================== test session starts =========================
tests/test_integration.py::TestLighterAdapterIntegration::test_get_market_info_eth PASSED
tests/test_integration.py::TestLighterAdapterIntegration::test_get_order_book_prices PASSED
tests/test_integration.py::test_full_workflow PASSED

======================== 8 passed in 3.21s ===========================
```

## Performance Benchmarks

### Expected Test Times

| Test Suite | Time | Notes |
|------------|------|-------|
| Unit tests | < 1s | No network calls |
| Integration tests | 3-5s | Depends on API latency |
| All tests | 4-6s | Combined |

### Caching Performance

Cache should provide ~10-100x speedup:

```
First API call:  ~200ms
Cached call:     ~2ms
```

## Test Coverage Goals

Aim for these coverage targets:

- **Base Interface:** 100% (complete coverage)
- **Factory:** 95%+ (all paths tested)
- **Adapters:** 80%+ (core functionality)
- **Integration:** 70%+ (happy paths)

## Writing New Tests

### Template for Adapter Tests

```python
import pytest
from your_adapter import YourAdapter

class TestYourAdapter:
    """Test suite for YourAdapter"""
    
    def test_adapter_name(self):
        """Test adapter returns correct name"""
        adapter = YourAdapter({})
        assert adapter.get_adapter_name() == "your_name"
    
    @pytest.mark.asyncio
    async def test_get_market_info(self):
        """Test market info fetch"""
        config = {...}
        adapter = YourAdapter(config)
        await adapter.initialize()
        
        try:
            info = await adapter.get_market_info(0)
            assert info.symbol is not None
        finally:
            await adapter.close()
```

## Best Practices

1. **Always use fixtures** for adapter instances
2. **Clean up** with try/finally or fixtures
3. **Mock external calls** for unit tests
4. **Use markers** to separate unit/integration tests
5. **Test error cases** not just happy paths
6. **Keep tests independent** - no shared state
7. **Use descriptive names** - test names explain what they test

## Next Steps

1. ✅ Run quick tests: `python run_adapter_tests.py quick`
2. ✅ Fix any failures
3. ✅ Run integration tests: `python run_adapter_tests.py integration`
4. ✅ Check coverage: `python run_adapter_tests.py unit --coverage`
5. ✅ Add tests for your custom adapters

## Summary

**Quick commands:**

```powershell
# Quick unit tests
python run_adapter_tests.py quick

# All unit tests with coverage
python run_adapter_tests.py unit --coverage

# Integration tests (requires credentials)
python run_adapter_tests.py integration

# Everything
python run_adapter_tests.py all -v
```

Now you're ready to test the adapter system! 🚀
