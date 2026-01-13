import logging
import asyncio
from typing import Dict, List, Any
from .base import BaseStrategy

logger = logging.getLogger(__name__)

class MonkStrategy(BaseStrategy):
    """
    Monk's Pair Trading Strategy (BTC/ETH).
    
    Logic:
    - Compare performance of BTC vs ETH.
    - If ETH pumps 2-3% more than BTC -> Long BTC / Short ETH (Mean Reversion).
    - If ETH dumps 2-3% more than BTC -> Short BTC / Long ETH.
    """
    
    def __init__(self, btc_symbol: str = "1", eth_symbol: str = "2", threshold_pct: float = 2.0):
        # Default Lighter IDs: WBTC=1, WETH=2 (Need to verify mapping in config)
        self.btc_symbol = btc_symbol
        self.eth_symbol = eth_symbol
        self.threshold = threshold_pct
        self.history = {} # To track price changes over time (or just use 24h change if available)

    def get_required_markets(self) -> List[str]:
        return [self.btc_symbol, self.eth_symbol]

    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        market_data should contain current prices or 24h stats for required markets.
        Structure expected:
        {
            '1': {'price': 50000, 'change_24h': 1.5},
            '2': {'price': 3000, 'change_24h': 4.5}
        }
        """
        btc_stats = market_data.get(self.btc_symbol)
        eth_stats = market_data.get(self.eth_symbol)

        if not btc_stats or not eth_stats:
            return {'should_trade': False, 'reason': 'Missing market data'}

        # Calculate relative performance
        # If we have 24h change from API, use that directly
        btc_change = btc_stats.get('change_24h', 0.0)
        eth_change = eth_stats.get('change_24h', 0.0)
        
        diff = eth_change - btc_change
        
        logger.info(f"Monk Strategy Analysis: BTC {btc_change:.2f}% | ETH {eth_change:.2f}% | Diff {diff:.2f}%")

        # Strategy 1: ETH Pumped more than BTC -> Long BTC / Short ETH
        if diff > self.threshold:
            return {
                'should_trade': True,
                'strategy': 'monk_reversion_short_eth',
                'markets': [self.btc_symbol, self.eth_symbol],
                'sides': ['buy', 'sell'], # Long BTC, Short ETH
                'reason': f"ETH outperformed BTC by {diff:.2f}%"
            }
            
        # Strategy 2: ETH Dumped more than BTC -> Short BTC / Long ETH
        elif diff < -self.threshold:
             return {
                'should_trade': True,
                'strategy': 'monk_reversion_long_eth',
                'markets': [self.btc_symbol, self.eth_symbol],
                'sides': ['sell', 'buy'], # Short BTC, Long ETH
                'reason': f"ETH underperformed BTC by {diff:.2f}%"
            }

        return {'should_trade': False, 'reason': 'No divergence'}
