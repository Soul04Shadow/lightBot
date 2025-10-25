"""
Quick adapter system test script.

Run this to verify the adapter system is working correctly
without needing to set up pytest.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from api_adapter_base import APIAdapterBase, MarketInfo, OrderResult
        from adapter_factory import AdapterFactory, AdapterManager
        from market_data_provider import MarketDataProvider
        from adapters.lighter_adapter import LighterAdapter
        print("  ✅ All imports successful")
        return True
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False


def test_data_structures():
    """Test data structure creation"""
    print("\nTesting data structures...")
    
    try:
        from api_adapter_base import MarketInfo, OrderResult, AccountBalance
        
        # Test MarketInfo
        info = MarketInfo(
            market_id=0,
            symbol="ETH-PERP",
            max_leverage=50,
            price_decimals=6,
            size_decimals=4,
        )
        assert info.symbol == "ETH-PERP"
        
        # Test OrderResult
        result = OrderResult(success=True, tx_hash="0xabc123")
        assert result.success is True
        
        # Test AccountBalance
        balance = AccountBalance(available_balance=1000.0, total_balance=1200.0)
        assert balance.available_balance == 1000.0
        
        print("  ✅ Data structures work correctly")
        return True
    except Exception as e:
        print(f"  ❌ Data structure test failed: {e}")
        return False


def test_adapter_factory():
    """Test adapter factory functionality"""
    print("\nTesting adapter factory...")
    
    try:
        from adapter_factory import AdapterFactory
        
        # Test getting available adapters
        adapters = AdapterFactory.get_available_adapters()
        assert isinstance(adapters, list)
        assert 'lighter' in adapters
        print(f"  Available adapters: {', '.join(adapters)}")
        
        # Test creating adapter
        config = {
            'base_url': 'https://testnet.zklighter.elliot.ai',
            'private_key': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
            'account_index': 1,
        }
        adapter = AdapterFactory.create_adapter('lighter', config)
        assert adapter is not None
        assert adapter.get_adapter_name() == 'lighter'
        
        print("  ✅ Adapter factory works correctly")
        return True
    except Exception as e:
        print(f"  ❌ Adapter factory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_lighter_adapter_config():
    """Test Lighter adapter configuration"""
    print("\nTesting Lighter adapter configuration...")
    
    try:
        from adapters.lighter_adapter import LighterAdapter
        
        # Test valid config
        valid_config = {
            'base_url': 'https://testnet.zklighter.elliot.ai',
            'private_key': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
            'account_index': 1,
        }
        
        adapter = LighterAdapter(valid_config)
        is_valid, error = adapter.validate_config(valid_config)
        assert is_valid is True
        assert error is None
        
        # Test invalid config (missing 0x prefix)
        invalid_config = {
            'base_url': 'https://testnet.zklighter.elliot.ai',
            'private_key': '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
            'account_index': 1,
        }
        
        is_valid, error = adapter.validate_config(invalid_config)
        assert is_valid is False
        assert '0x' in error
        
        print("  ✅ Lighter adapter configuration validation works")
        return True
    except Exception as e:
        print(f"  ❌ Lighter adapter config test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_market_data_provider():
    """Test market data provider"""
    print("\nTesting market data provider...")
    
    try:
        from market_data_provider import MarketDataProvider
        from unittest.mock import MagicMock, AsyncMock
        from api_adapter_base import MarketInfo
        
        # Create mock adapter
        mock_adapter = MagicMock()
        mock_adapter.get_market_info = AsyncMock(return_value=MarketInfo(
            market_id=0,
            symbol="ETH",
            max_leverage=50,
            price_decimals=6,
            size_decimals=4,
        ))
        
        provider = MarketDataProvider(mock_adapter, cache_ttl_seconds=60)
        
        # Test cache stats
        stats = provider.get_cache_stats()
        assert 'market_info_cached' in stats
        assert stats['cache_ttl_seconds'] == 60
        
        print("  ✅ Market data provider works correctly")
        return True
    except Exception as e:
        print(f"  ❌ Market data provider test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_async_initialization():
    """Test async adapter initialization (mock)"""
    print("\nTesting async adapter initialization...")
    
    try:
        from adapters.lighter_adapter import LighterAdapter
        
        config = {
            'base_url': 'https://testnet.zklighter.elliot.ai',
            'private_key': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
            'account_index': 1,
        }
        
        adapter = LighterAdapter(config)
        
        # Note: We can't actually initialize without valid credentials
        # Just verify the method exists and is callable
        assert hasattr(adapter, 'initialize')
        assert callable(adapter.initialize)
        assert hasattr(adapter, 'close')
        assert callable(adapter.close)
        
        print("  ✅ Async methods available")
        return True
    except Exception as e:
        print(f"  ❌ Async initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_configuration_loading():
    """Test loading configuration from environment"""
    print("\nTesting configuration loading...")
    
    try:
        import os
        from dotenv import load_dotenv
        
        # Try to load .env
        load_dotenv()
        
        # Check if credentials are available
        has_credentials = (
            os.getenv('ACCOUNT1_PRIVATE_KEY') is not None and
            os.getenv('ACCOUNT1_INDEX') is not None
        )
        
        if has_credentials:
            print("  ✅ Credentials found in .env")
            print("     You can run integration tests!")
        else:
            print("  ⚠️  No credentials in .env")
            print("     Integration tests will be skipped")
        
        return True
    except Exception as e:
        print(f"  ❌ Configuration loading test failed: {e}")
        return False


def main():
    """Run all quick tests"""
    print("="*70)
    print("  ADAPTER SYSTEM QUICK TEST")
    print("="*70)
    
    results = []
    
    # Run synchronous tests
    results.append(("Imports", test_imports()))
    results.append(("Data Structures", test_data_structures()))
    results.append(("Adapter Factory", test_adapter_factory()))
    results.append(("Lighter Config", test_lighter_adapter_config()))
    results.append(("Market Data Provider", test_market_data_provider()))
    results.append(("Configuration", test_configuration_loading()))
    
    # Run async test
    async_result = asyncio.run(test_async_initialization())
    results.append(("Async Initialization", async_result))
    
    # Print summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70 + "\n")
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}  {test_name}")
    
    total = len(results)
    passed_count = sum(1 for _, passed in results if passed)
    
    print(f"\n  Total: {passed_count}/{total} tests passed\n")
    
    if passed_count == total:
        print("  🎉 All tests passed! Adapter system is working correctly.")
        print("\n  Next steps:")
        print("  1. Run full test suite: python run_adapter_tests.py unit")
        print("  2. Try integration tests: python run_adapter_tests.py integration")
        print("  3. Check documentation: docs/TESTING_GUIDE.md")
        return 0
    else:
        print("  ⚠️  Some tests failed. Check errors above.")
        print("\n  Troubleshooting:")
        print("  1. Ensure all files are in the correct location")
        print("  2. Check imports work: python -c 'from adapter_factory import AdapterFactory'")
        print("  3. Review error messages above")
        return 1


if __name__ == '__main__':
    sys.exit(main())
