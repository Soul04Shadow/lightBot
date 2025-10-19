#!/usr/bin/env python3
"""
Test script to verify market whitelist functionality
"""

import asyncio
import sys

try:
    import pytest
    pytestmark = pytest.mark.skip(
        "test_market_whitelist is an integration script and not part of automated pytest suite"
    )
except ImportError:  # pragma: no cover - pytest not available in script mode
    pytest = None

from dotenv import load_dotenv
from config import BotConfig

# Explicitly load .env file
load_dotenv()

async def test_market_whitelist():
    """Test the market whitelist functionality"""
    print("="*70)
    print("Testing Market Whitelist Feature")
    print("="*70)
    
    try:
        # Load configuration
        config = BotConfig.from_env()
        
        print(f"\nConfiguration loaded:")
        print(f"  Base URL: {config.base_url}")
        print(f"  Market Whitelist: {config.market_whitelist}")
        print(f"  Number of markets: {len(config.market_whitelist)}")
        print(f"  Configured Leverage: {config.leverage}x")
        
        # Validate all whitelisted markets
        print(f"\nValidating all whitelisted markets...")
        await config.validate_with_api()
        
        print(f"\n✅ All validations passed!")
        print(f"\n{'='*70}")
        print("Market Selection Demo")
        print("="*70)
        print(f"Simulating 10 random market selections:")
        
        from delta_neutral_orchestrator import DeltaNeutralOrchestrator
        orchestrator = DeltaNeutralOrchestrator(config)
        
        # Simulate 10 random selections
        selection_counts = {market: 0 for market in config.market_whitelist}
        for i in range(10):
            selected = orchestrator.select_random_market()
            selection_counts[selected] += 1
            
            # Try to get market symbol
            try:
                market_info = await config.get_market_info(selected)
                symbol = market_info['symbol']
            except:
                symbol = f"Market {selected}"
                
            print(f"  Trade {i+1}: {symbol} (ID: {selected})")
        
        print(f"\nSelection distribution:")
        for market, count in selection_counts.items():
            percentage = (count / 10 * 100)
            try:
                market_info = await config.get_market_info(market)
                symbol = market_info['symbol']
            except:
                symbol = f"Market {market}"
            print(f"  {symbol} (ID: {market}): {count}/10 ({percentage:.0f}%)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_market_whitelist())
    sys.exit(0 if success else 1)
