from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.
    Decides *what* to trade and *when*.
    """

    @abstractmethod
    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market data and return trade signal.
        Returns a dict containing:
        - 'should_trade': bool
        - 'direction': 'long_short' or 'neutral'
        - 'markets': list of symbols/ids to trade
        - 'sides': list of 'buy'/'sell' corresponding to markets
        """
        pass

    @abstractmethod
    def get_required_markets(self) -> List[str]:
        """Return list of symbols this strategy watches."""
        pass
