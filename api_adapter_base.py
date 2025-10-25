"""
Base API Adapter Interface

Abstract base class defining the interface that all DEX API adapters must implement.
This allows the bot to work with different DEX platforms by implementing this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class MarketInfo:
    """Standardized market information structure"""
    market_id: int
    symbol: str
    max_leverage: int
    price_decimals: int
    size_decimals: int
    min_order_size: Optional[float] = None
    max_order_size: Optional[float] = None
    tick_size: Optional[float] = None


@dataclass
class OrderResult:
    """Standardized order execution result"""
    success: bool
    tx_hash: Optional[str] = None
    error: Optional[str] = None
    order_id: Optional[str] = None


@dataclass
class AccountBalance:
    """Standardized account balance information"""
    available_balance: float
    total_balance: float
    margin_used: Optional[float] = None
    unrealized_pnl: Optional[float] = None


@dataclass
class Position:
    """Standardized position information"""
    market_id: int
    size: float
    entry_price: float
    is_long: bool
    unrealized_pnl: Optional[float] = None
    leverage: Optional[int] = None


@dataclass
class OrderBookPrice:
    """Order book pricing information"""
    best_bid: Optional[float]
    best_ask: Optional[float]
    mid_price: Optional[float] = None


class APIAdapterBase(ABC):
    """
    Abstract base class for DEX API adapters.
    
    All DEX-specific implementations must inherit from this class
    and implement all abstract methods.
    """
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the API client and authenticate.
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Clean up resources and close connections"""
        pass
    
    # Market Data Methods
    
    @abstractmethod
    async def get_market_info(self, market_id: int) -> MarketInfo:
        """
        Fetch comprehensive market information.
        
        Args:
            market_id: Market identifier
            
        Returns:
            MarketInfo object with market details
            
        Raises:
            Exception if market info cannot be retrieved
        """
        pass
    
    @abstractmethod
    async def get_order_book_prices(self, market_id: int) -> OrderBookPrice:
        """
        Get current best bid/ask prices from order book.
        
        Args:
            market_id: Market identifier
            
        Returns:
            OrderBookPrice with current pricing
            
        Raises:
            Exception if prices cannot be retrieved
        """
        pass
    
    @abstractmethod
    async def get_size_decimals(self, market_id: int) -> int:
        """
        Get the precision/decimals for order sizing on this market.
        
        Args:
            market_id: Market identifier
            
        Returns:
            Number of decimal places for order sizes
        """
        pass
    
    # Account Methods
    
    @abstractmethod
    async def get_account_balance(self, account_index: int) -> AccountBalance:
        """
        Fetch account balance information.
        
        Args:
            account_index: Account identifier
            
        Returns:
            AccountBalance with balance details
            
        Raises:
            Exception if balance cannot be retrieved
        """
        pass
    
    @abstractmethod
    async def get_account_positions(self, account_index: int, market_id: Optional[int] = None) -> list[Position]:
        """
        Get open positions for an account.
        
        Args:
            account_index: Account identifier
            market_id: Optional market filter
            
        Returns:
            List of Position objects
        """
        pass
    
    # Trading Methods
    
    @abstractmethod
    async def update_leverage(
        self,
        market_id: int,
        leverage: int,
        margin_mode: int  # 0 = cross, 1 = isolated
    ) -> Tuple[bool, Optional[str]]:
        """
        Update leverage settings for a market.
        
        Args:
            market_id: Market identifier
            leverage: Leverage multiplier
            margin_mode: 0 for cross margin, 1 for isolated
            
        Returns:
            Tuple of (success, error_message)
        """
        pass
    
    @abstractmethod
    async def create_market_order(
        self,
        market_id: int,
        base_amount: int,
        is_ask: bool,
        execution_price: int,
        reduce_only: bool = False,
        client_order_id: Optional[int] = None
    ) -> OrderResult:
        """
        Create and execute a market order.
        
        Args:
            market_id: Market identifier
            base_amount: Order size in market's base units
            is_ask: True for sell/short, False for buy/long
            execution_price: Worst acceptable execution price (slippage protection)
            reduce_only: If True, order can only reduce position size
            client_order_id: Optional client-side order identifier
            
        Returns:
            OrderResult with execution details
        """
        pass
    
    # Configuration Methods
    
    @abstractmethod
    def get_adapter_name(self) -> str:
        """Return the name of this adapter (e.g., 'lighter', 'paradex')"""
        pass
    
    @abstractmethod
    def get_required_config_keys(self) -> list[str]:
        """
        Return list of required configuration keys for this adapter.
        
        Returns:
            List of environment variable names needed
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate adapter-specific configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    # Optional: Helper methods that can be overridden
    
    def supports_batch_orders(self) -> bool:
        """
        Whether this adapter supports batch order submission.
        
        Returns:
            True if batch orders are supported
        """
        return False
    
    def get_default_base_url(self) -> str:
        """
        Get the default API base URL (testnet).
        
        Returns:
            Default base URL string
        """
        return ""
    
    def get_mainnet_base_url(self) -> str:
        """
        Get the mainnet API base URL.
        
        Returns:
            Mainnet base URL string
        """
        return ""
