from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional

class ExchangeClient(ABC):
    """
    Abstract base class for all exchange implementations.
    Ensures that Lighter, Binance, etc. all look the same to the bot.
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize connections/signers."""
        pass

    @abstractmethod
    async def get_balance(self) -> float:
        """Return available USDT/Collateral balance."""
        pass

    @abstractmethod
    async def get_orderbook_price(self, symbol: str) -> Tuple[float, float]:
        """Return (best_bid, best_ask)."""
        pass

    @abstractmethod
    async def create_market_order(self, 
                                symbol: str, 
                                side: str, 
                                size: float, 
                                price_limit: float = None,
                                params: Dict = None) -> Dict:
        """
        Execute a market order.
        side: 'buy' or 'sell'
        """
        pass

    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int, margin_mode: str) -> bool:
        """Set leverage for a market."""
        pass

    @abstractmethod
    async def get_market_precision(self, symbol: str) -> int:
        """Get the number of decimals for volume/size."""
        pass

    @abstractmethod
    async def close(self):
        """Cleanup."""
        pass
