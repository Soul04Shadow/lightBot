import logging
import asyncio
from typing import Dict, Tuple, Optional
from .base import ExchangeClient

logger = logging.getLogger(__name__)

class LighterExchange(ExchangeClient):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
        self.api_client = None
        # Lazy import to avoid hard dependency at module level if possible, 
        # or just standard import if we assume requirements are met.
        import lighter
        self.lighter = lighter

    async def initialize(self) -> bool:
        try:
            # If we have a private key, we initialize the SignerClient (Write access)
            if self.config.get('private_key'):
                self.client = self.lighter.SignerClient(
                    url=self.config['base_url'],
                    private_key=self.config['private_key'],
                    account_index=self.config.get('account_index', 0),
                    api_key_index=self.config.get('api_key_index', 0),
                )
            
            # For read-only operations (price checking), we might use a plain ApiClient
            # But the SignerClient often wraps it. 
            # If we are in "Orchestrator Mode" (no private key), we need a basic client.
            else:
                configuration = self.lighter.Configuration(self.config['base_url'])
                self.api_client = self.lighter.ApiClient(configuration)

            return True
        except Exception as e:
            logger.error(f"Failed to init LighterExchange: {e}")
            return False

    async def get_balance(self) -> float:
        # Note: Lighter's Account API usage
        try:
            if self.client:
                # SignerClient might not expose account balance directly without calling the generic API?
                # Looking at original code: account_api.account(by="index", ...)
                # The SignerClient usually facilitates order creation. 
                # For safety, let's use the patterns from the original code.
                pass
            
            # Reusing the logic from Orchestrator:
            # account_api = lighter.AccountApi(api_client)
            client_to_use = self.client.api_client if self.client else self.api_client
            if not client_to_use: return 0.0

            account_api = self.lighter.AccountApi(client_to_use)
            
            # If we are a worker, we know our index
            idx = self.config.get('account_index')
            if idx is None: return 0.0

            acc_data = await account_api.account(by="index", value=str(idx))
            if acc_data.accounts:
                return float(acc_data.accounts[0].available_balance)
            return 0.0
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return 0.0

    async def get_orderbook_price(self, symbol: str) -> Tuple[float, float]:
        # Symbol in Lighter is usually an integer market_id
        try:
            market_id = int(symbol)
            client_to_use = self.client.api_client if self.client else self.api_client
            if not client_to_use: return (0.0, 0.0)

            order_api = self.lighter.OrderApi(client_to_use)
            order_book = await order_api.order_book_orders(market_id=market_id, limit=1)
            
            best_bid = float(order_book.bids[0].price) if order_book.bids else 0.0
            best_ask = float(order_book.asks[0].price) if order_book.asks else 0.0
            return best_bid, best_ask
        except Exception as e:
            logger.error(f"Error fetching ticker: {e}")
            return (0.0, 0.0)

    async def create_market_order(self, 
                                symbol: str, 
                                side: str, 
                                size: float, 
                                price_limit: float = None,
                                params: Dict = None) -> Dict:
        if not self.client:
            return {'success': False, 'error': 'No write access'}

        try:
            market_id = int(symbol)
            is_ask = (side.lower() == 'sell')
            
            # Default params handling
            params = params or {}
            client_order_index = params.get('client_order_index', int(asyncio.get_event_loop().time() * 1000))
            reduce_only = params.get('reduce_only', False)

            result = await self.client.create_market_order(
                market_index=market_id,
                client_order_index=client_order_index,
                base_amount=size,
                avg_execution_price=price_limit, # This is crucial for Lighter's "Market" orders (they are limit-like)
                is_ask=is_ask,
                reduce_only=reduce_only
            )
            
            create_order, resp, error = result
            if error:
                 return {'success': False, 'error': str(error)}
            
            if resp and resp.code == 200:
                return {'success': True, 'tx_hash': resp.tx_hash}
            
            return {'success': False, 'error': f"API Error {resp.code if resp else 'N/A'}"}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def set_leverage(self, symbol: str, leverage: int, margin_mode: str) -> bool:
        if not self.client: return False
        try:
            market_id = int(symbol)
            mode_int = 1 if margin_mode == 'isolated' else 0
            
            await self.client.update_leverage(
                market_index=market_id,
                margin_mode=mode_int,
                leverage=leverage
            )
            return True
        except Exception as e:
            logger.error(f"Leverage update failed: {e}")
            return False

    async def get_market_precision(self, symbol: str) -> int:
        try:
            market_id = int(symbol)
            # Use cached precision if available in config? 
            # Or fetch from API. The orchestrator logic had a good fallback.
            # Let's try to fetch order book details.
            
            client_to_use = self.client.api_client if self.client else self.api_client
            if not client_to_use: return 0
            
            order_api = self.lighter.OrderApi(client_to_use)
            details = await order_api.order_book_details(market_id=market_id)
            
            if details.order_book_details:
                for d in details.order_book_details:
                    if d.market_id == market_id:
                        return d.size_decimals
            return 0 # Caller should handle fallback
        except Exception as e:
            logger.warning(f"Could not fetch precision: {e}")
            return 0

    async def close(self):
        if self.client:
            await self.client.close()
        elif self.api_client:
            await self.api_client.close()
