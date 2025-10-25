"""
Lighter DEX API Adapter

Implementation of the API adapter for Lighter DEX.
This wraps the lighter-python SDK into our standardized interface.
"""

import logging
from typing import Dict, Any, Optional, Tuple

import lighter

from api_adapter_base import (
    APIAdapterBase,
    MarketInfo,
    OrderResult,
    AccountBalance,
    Position,
    OrderBookPrice,
)

logger = logging.getLogger(__name__)


class LighterAdapter(APIAdapterBase):
    """API adapter for Lighter DEX"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Lighter adapter.
        
        Args:
            config: Configuration dictionary with keys:
                - base_url: API endpoint
                - private_key: Account private key
                - account_index: Account index
                - api_key_index: API key index
        """
        self.config = config
        self.client: Optional[lighter.SignerClient] = None
        self._last_leverage_request: Optional[Tuple[int, int, int]] = None
    
    async def initialize(self) -> bool:
        """Initialize the Lighter SignerClient"""
        try:
            self.client = lighter.SignerClient(
                url=self.config['base_url'],
                private_key=self.config['private_key'],
                account_index=self.config['account_index'],
                api_key_index=self.config.get('api_key_index', 0),
            )
            logger.info(
                "Initialized Lighter adapter for account %s",
                self.config['account_index']
            )
            return True
        except Exception as e:
            logger.error("Failed to initialize Lighter adapter: %s", e)
            return False
    
    async def close(self) -> None:
        """Close the Lighter client connection"""
        if self.client:
            await self.client.close()
            self.client = None
    
    # Market Data Methods
    
    async def get_market_info(self, market_id: int) -> MarketInfo:
        """Fetch market information from Lighter API"""
        try:
            configuration = lighter.Configuration(self.config['base_url'])
            api_client = lighter.ApiClient(configuration)
            order_api = lighter.OrderApi(api_client)
            
            order_book_details = await order_api.order_book_details(market_id=market_id)
            
            await api_client.close()
            
            if order_book_details.order_book_details:
                for detail in order_book_details.order_book_details:
                    if detail.market_id == market_id:
                        # Calculate max leverage from margin fraction
                        min_margin_fraction = detail.min_initial_margin_fraction / 10000.0
                        max_leverage = int(1.0 / min_margin_fraction)
                        
                        # Get price decimals
                        price_decimals = getattr(detail, 'price_decimals', None)
                        if price_decimals is None:
                            price_decimals = getattr(detail, 'supported_price_decimals', 6)
                        
                        # Get size decimals
                        size_decimals = getattr(detail, 'size_decimals', 4)
                        
                        return MarketInfo(
                            market_id=market_id,
                            symbol=detail.symbol,
                            max_leverage=max_leverage,
                            price_decimals=price_decimals or 6,
                            size_decimals=size_decimals,
                        )
                
                raise ValueError(f"Market {market_id} not found in order book details")
            else:
                raise ValueError("No order book details returned from API")
                
        except Exception as e:
            raise Exception(f"Failed to fetch market info for market {market_id}: {e}")
    
    async def get_order_book_prices(self, market_id: int) -> OrderBookPrice:
        """Get best bid/ask from Lighter order book"""
        try:
            configuration = lighter.Configuration(self.config['base_url'])
            api_client = lighter.ApiClient(configuration)
            order_api = lighter.OrderApi(api_client)
            
            order_book = await order_api.order_book(market_id=market_id)
            
            await api_client.close()
            
            best_bid = None
            best_ask = None
            
            if order_book.order_book:
                if order_book.order_book.bids:
                    best_bid = float(order_book.order_book.bids[0].price)
                if order_book.order_book.asks:
                    best_ask = float(order_book.order_book.asks[0].price)
            
            mid_price = None
            if best_bid and best_ask:
                mid_price = (best_bid + best_ask) / 2
            
            return OrderBookPrice(
                best_bid=best_bid,
                best_ask=best_ask,
                mid_price=mid_price,
            )
            
        except Exception as e:
            raise Exception(f"Failed to fetch order book for market {market_id}: {e}")
    
    async def get_size_decimals(self, market_id: int) -> int:
        """Get size decimals from market info"""
        market_info = await self.get_market_info(market_id)
        return market_info.size_decimals
    
    # Account Methods
    
    async def get_account_balance(self, account_index: int) -> AccountBalance:
        """Fetch account balance from Lighter API"""
        try:
            configuration = lighter.Configuration(self.config['base_url'])
            api_client = lighter.ApiClient(configuration)
            account_api = lighter.AccountApi(api_client)
            
            account_data = await account_api.account(
                by="index",
                value=str(account_index),
            )
            
            await api_client.close()
            
            if account_data.accounts:
                acc = account_data.accounts[0]
                return AccountBalance(
                    available_balance=float(acc.available_balance),
                    total_balance=float(acc.total_balance) if hasattr(acc, 'total_balance') else float(acc.available_balance),
                    margin_used=float(acc.margin_used) if hasattr(acc, 'margin_used') else None,
                    unrealized_pnl=float(acc.unrealized_pnl) if hasattr(acc, 'unrealized_pnl') else None,
                )
            else:
                raise ValueError(f"No account data found for index {account_index}")
                
        except Exception as e:
            raise Exception(f"Failed to fetch balance for account {account_index}: {e}")
    
    async def get_account_positions(self, account_index: int, market_id: Optional[int] = None) -> list[Position]:
        """Get open positions for account"""
        try:
            configuration = lighter.Configuration(self.config['base_url'])
            api_client = lighter.ApiClient(configuration)
            account_api = lighter.AccountApi(api_client)
            
            account_data = await account_api.account(
                by="index",
                value=str(account_index),
            )
            
            await api_client.close()
            
            positions = []
            if account_data.accounts and account_data.accounts[0].positions:
                for pos in account_data.accounts[0].positions:
                    # Filter by market if specified
                    if market_id is not None and pos.market_id != market_id:
                        continue
                    
                    size = float(pos.size)
                    positions.append(Position(
                        market_id=pos.market_id,
                        size=abs(size),
                        entry_price=float(pos.entry_price) if hasattr(pos, 'entry_price') else 0.0,
                        is_long=size > 0,
                        unrealized_pnl=float(pos.unrealized_pnl) if hasattr(pos, 'unrealized_pnl') else None,
                        leverage=int(pos.leverage) if hasattr(pos, 'leverage') else None,
                    ))
            
            return positions
            
        except Exception as e:
            logger.warning("Failed to fetch positions for account %s: %s", account_index, e)
            return []
    
    # Trading Methods
    
    async def update_leverage(
        self,
        market_id: int,
        leverage: int,
        margin_mode: int
    ) -> Tuple[bool, Optional[str]]:
        """Update leverage settings on Lighter"""
        try:
            if not self.client:
                return False, "Client not initialized"
            
            # Check if this is the same as last request (avoid redundant updates)
            last_request = self._last_leverage_request
            current_request = (market_id, leverage, margin_mode)
            
            if last_request == current_request:
                logger.info(
                    "Skipping leverage update for market %s: unchanged (leverage=%s, margin_mode=%s)",
                    market_id,
                    leverage,
                    margin_mode,
                )
                return True, None
            
            await self.client.update_leverage(
                market_index=market_id,
                margin_mode=margin_mode,
                leverage=leverage
            )
            
            self._last_leverage_request = current_request
            logger.info(
                "Updated leverage for market %s: leverage=%sx, margin_mode=%s",
                market_id,
                leverage,
                "cross" if margin_mode == 0 else "isolated",
            )
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to update leverage: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    async def create_market_order(
        self,
        market_id: int,
        base_amount: int,
        is_ask: bool,
        execution_price: int,
        reduce_only: bool = False,
        client_order_id: Optional[int] = None
    ) -> OrderResult:
        """Execute a market order on Lighter"""
        try:
            if not self.client:
                return OrderResult(success=False, error="Client not initialized")
            
            # Use a default client order ID if not provided
            if client_order_id is None:
                import random
                client_order_id = random.randint(1, 2**31 - 1)
            
            result = await self.client.create_market_order(
                market_index=market_id,
                client_order_index=client_order_id,
                base_amount=base_amount,
                avg_execution_price=execution_price,
                is_ask=is_ask,
                reduce_only=reduce_only
            )
            
            create_order, resp, error = result
            
            if error:
                return OrderResult(success=False, error=str(error))
            
            if resp and resp.code == 200:
                return OrderResult(
                    success=True,
                    tx_hash=resp.tx_hash,
                    order_id=str(client_order_id),
                )
            
            error_msg = f"API Error {resp.code if resp else 'N/A'}"
            if resp and resp.message:
                error_msg += f": {resp.message}"
            return OrderResult(success=False, error=error_msg)
            
        except Exception as e:
            return OrderResult(success=False, error=str(e))
    
    # Configuration Methods
    
    def get_adapter_name(self) -> str:
        """Return adapter name"""
        return "lighter"
    
    def get_required_config_keys(self) -> list[str]:
        """Return required configuration keys"""
        return [
            'base_url',
            'private_key',
            'account_index',
        ]
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate Lighter-specific configuration"""
        required_keys = self.get_required_config_keys()
        
        for key in required_keys:
            if key not in config:
                return False, f"Missing required config key: {key}"
        
        # Validate and normalize private key format
        private_key = config['private_key']
        if not private_key.startswith('0x'):
            # Auto-add 0x prefix if missing for convenience
            config['private_key'] = f"0x{private_key}"
        
        # Validate account index is non-negative
        try:
            account_index = int(config['account_index'])
            if account_index < 0:
                return False, "account_index must be non-negative"
        except (ValueError, TypeError):
            return False, "account_index must be a valid integer"
        
        return True, None
    
    # Helper methods
    
    def get_default_base_url(self) -> str:
        """Get default Lighter testnet URL"""
        return "https://testnet.zklighter.elliot.ai"
    
    def get_mainnet_base_url(self) -> str:
        """Get Lighter mainnet URL"""
        return "https://mainnet.zklighter.elliot.ai"
