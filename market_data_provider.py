"""
Adapter-Agnostic Market Data Provider

Provides market data access through the configured API adapter,
abstracting away DEX-specific implementations.
"""

import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

from api_adapter_base import APIAdapterBase, MarketInfo, OrderBookPrice, AccountBalance

logger = logging.getLogger(__name__)


@dataclass
class MarketDataCache:
    """Cache for market metadata with TTL"""
    info: MarketInfo
    timestamp: float


class MarketDataProvider:
    """
    Provides market data through an API adapter with caching support.
    
    This class abstracts market data access to work with any DEX adapter.
    """
    
    def __init__(
        self,
        adapter: APIAdapterBase,
        cache_ttl_seconds: int = 300
    ):
        """
        Initialize market data provider.
        
        Args:
            adapter: API adapter instance
            cache_ttl_seconds: Time-to-live for cached data in seconds
        """
        self.adapter = adapter
        self.cache_ttl_seconds = cache_ttl_seconds
        self._market_info_cache: Dict[int, MarketDataCache] = {}
        self._size_decimals_cache: Dict[int, Tuple[int, float]] = {}
    
    def _current_time(self) -> float:
        """Get current timestamp"""
        import time
        return time.time()
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cached data is still valid"""
        return (self._current_time() - timestamp) < self.cache_ttl_seconds
    
    async def get_market_info(self, market_id: int, use_cache: bool = True) -> MarketInfo:
        """
        Get comprehensive market information.
        
        Args:
            market_id: Market identifier
            use_cache: Whether to use cached data if available
            
        Returns:
            MarketInfo object with market details
        """
        # Check cache first
        if use_cache and market_id in self._market_info_cache:
            cached = self._market_info_cache[market_id]
            if self._is_cache_valid(cached.timestamp):
                logger.debug("Using cached market info for market %s", market_id)
                return cached.info
            else:
                logger.debug("Cached market info expired for market %s", market_id)
        
        # Fetch fresh data
        logger.info("Fetching market info for market %s from API", market_id)
        info = await self.adapter.get_market_info(market_id)
        
        # Cache the result
        self._market_info_cache[market_id] = MarketDataCache(
            info=info,
            timestamp=self._current_time()
        )
        
        return info
    
    async def get_size_decimals(self, market_id: int, use_cache: bool = True) -> int:
        """
        Get size decimals for a market.
        
        Args:
            market_id: Market identifier
            use_cache: Whether to use cached data
            
        Returns:
            Number of decimal places for order sizes
        """
        # Check cache first
        if use_cache and market_id in self._size_decimals_cache:
            decimals, timestamp = self._size_decimals_cache[market_id]
            if self._is_cache_valid(timestamp):
                logger.debug("Using cached size decimals for market %s", market_id)
                return decimals
        
        # Fetch from market info
        info = await self.get_market_info(market_id, use_cache=use_cache)
        
        # Cache the result
        self._size_decimals_cache[market_id] = (info.size_decimals, self._current_time())
        
        return info.size_decimals
    
    async def get_order_book_prices(self, market_id: int) -> OrderBookPrice:
        """
        Get current order book prices.
        
        Args:
            market_id: Market identifier
            
        Returns:
            OrderBookPrice with current bid/ask
        """
        return await self.adapter.get_order_book_prices(market_id)
    
    async def get_account_balance(self, account_index: int) -> AccountBalance:
        """
        Get account balance.
        
        Args:
            account_index: Account identifier
            
        Returns:
            AccountBalance with balance information
        """
        return await self.adapter.get_account_balance(account_index)
    
    def clear_cache(self, market_id: Optional[int] = None) -> None:
        """
        Clear cached market data.
        
        Args:
            market_id: If provided, clear only this market's cache.
                      Otherwise, clear all cached data.
        """
        if market_id is not None:
            self._market_info_cache.pop(market_id, None)
            self._size_decimals_cache.pop(market_id, None)
            logger.info("Cleared cache for market %s", market_id)
        else:
            self._market_info_cache.clear()
            self._size_decimals_cache.clear()
            logger.info("Cleared all market data cache")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'market_info_cached': len(self._market_info_cache),
            'size_decimals_cached': len(self._size_decimals_cache),
            'cache_ttl_seconds': self.cache_ttl_seconds,
        }
