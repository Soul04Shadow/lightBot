# How to Test the API Adapter System

## TL;DR - Quick Start

```powershell
# 1. Quick verification (no API calls)
python quick_test_adapters.py

# 2. Run unit tests
python run_adapter_tests.py quick

# 3. If you have credentials, run integration tests
python run_adapter_tests.py integration
```

## What Tests Are Available?

### 1. Quick Test Script ⚡
**File:** `quick_test_adapters.py`

**What it does:**
- Verifies all imports work
- Tests data structures
- Tests adapter factory
- Tests configuration validation
- NO API calls - runs offline

**When to use:** First time setup, quick sanity check

**Run:**
```powershell
python quick_test_adapters.py
```

**Expected output:**
```
======================================================================
  ADAPTER SYSTEM QUICK TEST
======================================================================

Testing imports...
  ✅ All imports successful

Testing data structures...
  ✅ Data structures work correctly

Testing adapter factory...
  Available adapters: lighter, paradex
  ✅ Adapter factory works correctly

...

  Total: 7/7 tests passed

  🎉 All tests passed! Adapter system is working correctly.
```

### 2. Unit Tests 🧪
**Files:** `tests/test_*.py`

**What it does:**
- Tests base interface
- Tests adapter factory
- Tests Lighter adapter
- Tests market data provider
- Uses mocks - NO real API calls

**When to use:** Development, CI/CD, pre-commit

**Run:**
```powershell
# All unit tests
python run_adapter_tests.py unit

# Specific test file
pytest tests/test_adapter_base.py -v

# With coverage
python run_adapter_tests.py unit --coverage
```

### 3. Integration Tests 🌐
**File:** `tests/test_integration.py`

**What it does:**
- Makes REAL API calls to testnet
- Tests actual Lighter DEX integration
- Validates end-to-end workflows
- Requires valid credentials

**When to use:** Before deployment, verifying API changes

**⚠️ Requirements:**
- Valid `.env` file with credentials
- Network connectivity
- Testnet account with balance

**Run:**
```powershell
python run_adapter_tests.py integration
```

## Step-by-Step Testing

### Step 1: Install Dependencies

```powershell
# Install test framework
pip install pytest pytest-asyncio pytest-cov

# Or install everything
pip install -r requirements.txt
```

### Step 2: Run Quick Test

```powershell
python quick_test_adapters.py
```

**If this passes:** Core system is working ✅

**If this fails:** Check file locations and imports

### Step 3: Run Unit Tests

```powershell
python run_adapter_tests.py unit -v
```

**What you should see:**
```
============================ test session starts ============================

tests/test_adapter_base.py::test_market_info_creation PASSED         [ 5%]
tests/test_adapter_base.py::test_order_result_success PASSED         [10%]
tests/test_adapter_factory.py::test_create_lighter_adapter PASSED    [15%]
...

============================ 20 passed in 0.45s =============================
```

### Step 4: Setup for Integration Tests (Optional)

**Create/update `.env`:**
```env
BASE_URL=https://testnet.zklighter.elliot.ai
ACCOUNT1_PRIVATE_KEY=0x...your_testnet_key...
ACCOUNT1_INDEX=123456
ACCOUNT1_API_KEY_INDEX=0
```

**Verify credentials:**
```powershell
python check_balances.py
```

### Step 5: Run Integration Tests

```powershell
python run_adapter_tests.py integration -v
```

**What you should see:**
```
============================ test session starts ============================

tests/test_integration.py::test_get_market_info_eth PASSED           [12%]
tests/test_integration.py::test_get_order_book_prices PASSED         [25%]
tests/test_integration.py::test_get_account_balance PASSED           [37%]
...

============================ 8 passed in 3.21s ==============================
```

## Test Organization

```
tests/
├── test_adapter_base.py          # 8 tests  - Base interface
├── test_adapter_factory.py       # 12 tests - Factory & manager
├── test_lighter_adapter.py       # 10 tests - Lighter adapter
├── test_market_data_provider.py  # 8 tests  - Data provider
└── test_integration.py           # 8 tests  - Real API calls

Total: 46 unit tests + 8 integration tests = 54 tests
```

## Testing Specific Components

### Test Only Factory

```powershell
pytest tests/test_adapter_factory.py -v
```

### Test Only Lighter Adapter

```powershell
pytest tests/test_lighter_adapter.py -v
```

### Test Only Caching

```powershell
pytest tests/test_market_data_provider.py -v
```

### Test Specific Function

```powershell
pytest tests/test_adapter_factory.py::TestAdapterFactory::test_create_lighter_adapter -v
```

## Coverage Analysis

### Generate Coverage Report

```powershell
python run_adapter_tests.py unit --coverage
```

### View Coverage

```powershell
# Open HTML report
start htmlcov/index.html

# Or view in terminal
pytest tests/ --cov=. --cov-report=term
```

### Coverage Goals

- ✅ Base interface: 100%
- ✅ Factory: 95%+
- ✅ Adapters: 80%+
- ✅ Overall: 85%+

## Manual Testing

### Test Adapter Creation

```powershell
python -c "from adapter_factory import AdapterFactory; print(AdapterFactory.get_available_adapters())"
```

### Test With Existing Scripts

```powershell
# These should still work
python check_balances.py
python test_market_whitelist.py
```

### Interactive Testing

```powershell
# Start Python REPL
python

# Then in Python:
>>> from adapter_factory import AdapterFactory
>>> adapters = AdapterFactory.get_available_adapters()
>>> print(adapters)
['lighter', 'paradex']

>>> config = {
...     'base_url': 'https://testnet.zklighter.elliot.ai',
...     'private_key': '0x1234...',
...     'account_index': 1,
... }
>>> adapter = AdapterFactory.create_adapter('lighter', config)
>>> adapter.get_adapter_name()
'lighter'
```

## Continuous Testing

### Watch Mode (Auto-run on file changes)

```powershell
# Install pytest-watch
pip install pytest-watch

# Run in watch mode
ptw tests/ -- -v
```

### Run Before Each Commit

Create `.git/hooks/pre-commit`:

```bash
#!/bin/sh
echo "Running tests before commit..."
python run_adapter_tests.py unit || exit 1
```

## Common Test Scenarios

### Scenario 1: New Adapter Development

```powershell
# 1. Create adapter
# 2. Test it works
pytest tests/test_your_adapter.py -v

# 3. Run all tests
python run_adapter_tests.py unit

# 4. Test integration
python run_adapter_tests.py integration
```

### Scenario 2: Before Deployment

```powershell
# Full test suite
python run_adapter_tests.py all -v

# Generate coverage report
python run_adapter_tests.py unit --coverage

# Review coverage
start htmlcov/index.html
```

### Scenario 3: Debugging Issue

```powershell
# Run specific test with verbose output
pytest tests/test_adapter_factory.py::TestAdapterFactory::test_create_adapter -vv

# Run with print statements visible
pytest tests/test_adapter_factory.py -v -s

# Run with debugger
pytest tests/test_adapter_factory.py --pdb
```

## Troubleshooting

### Tests Not Found

**Problem:** `pytest: no tests ran`

**Solution:**
```powershell
# Check test files exist
ls tests/test_*.py

# Try full path
pytest tests/test_adapter_base.py
```

### Import Errors

**Problem:** `ImportError: cannot import name 'AdapterFactory'`

**Solution:**
```powershell
# Add current directory to path
$env:PYTHONPATH = "."

# Or run from project root
cd "e:\Volume Generation Bot Paradex"
python run_adapter_tests.py unit
```

### Async Warnings

**Problem:** `RuntimeWarning: coroutine was never awaited`

**Solution:**
```powershell
# Install pytest-asyncio
pip install pytest-asyncio

# Mark tests with @pytest.mark.asyncio
```

### Integration Tests Failing

**Problem:** `ValueError: Missing required config key`

**Solution:**
```powershell
# Check .env file
cat .env

# Verify credentials work
python check_balances.py

# Run with specific env file
$env:ENV_FILE = ".env.testnet"
python run_adapter_tests.py integration
```

## Expected Test Times

| Test Type | Duration | API Calls |
|-----------|----------|-----------|
| Quick test | < 1s | None |
| Unit tests | < 1s | None |
| Integration tests | 3-5s | Yes |
| All tests | 4-6s | Yes (integration) |
| With coverage | +1-2s | None (unit only) |

## Test Success Criteria

### ✅ All Green

```
======================== 54 passed in 4.23s =========================
```

Means:
- All unit tests passed
- All integration tests passed (if run)
- No errors or warnings
- System is working correctly

### ⚠️ Some Yellow (Warnings)

```
==================== 54 passed, 3 warnings in 4.23s ====================
```

Means:
- Tests passed but with warnings
- Usually deprecation warnings
- Review warnings but not critical

### ❌ Red (Failures)

```
==================== 45 passed, 9 failed in 4.23s ====================
```

Means:
- Some tests failed
- Review failure details
- Fix issues before proceeding

## Summary Commands

```powershell
# Complete test workflow

# 1. Quick check
python quick_test_adapters.py

# 2. Unit tests
python run_adapter_tests.py unit

# 3. Integration tests (if credentials available)
python run_adapter_tests.py integration

# 4. Coverage report
python run_adapter_tests.py unit --coverage

# 5. View coverage
start htmlcov/index.html
```

## Next Steps After Testing

1. ✅ All tests pass → Ready to use adapters
2. ✅ Create your own adapter → See `docs/API_ADAPTER_GUIDE.md`
3. ✅ Integrate with bot → Update orchestrator
4. ✅ Deploy → Test on testnet first

## Resources

- **Full Guide:** [`docs/TESTING_GUIDE.md`](docs/TESTING_GUIDE.md)
- **Adapter Guide:** [`docs/API_ADAPTER_GUIDE.md`](docs/API_ADAPTER_GUIDE.md)
- **Quick Reference:** [`ADAPTER_QUICK_REFERENCE.md`](ADAPTER_QUICK_REFERENCE.md)

---

**Ready to test?** Run: `python quick_test_adapters.py` 🚀
