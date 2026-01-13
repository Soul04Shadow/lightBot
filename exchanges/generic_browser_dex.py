import logging
import asyncio
from typing import Dict, Tuple, Any
from .browser_exchange import BrowserExchange

logger = logging.getLogger(__name__)

class GenericBrowserDex(BrowserExchange):
    """
    Example implementation for a generic UI-based DEX.
    Config requires standard selectors for finding price and buttons.
    """
    
    async def _post_launch_setup(self):
        # Example: Wait for the main trading interface to load
        # In a real scenario, you might have to click "Connect Wallet" here
        # or handle a Metamask popup using a separate extension driver.
        logger.info("Waiting for exchange UI to load...")
        try:
             # Wait for a common element like a "Trade" button or header
             await self.page.wait_for_selector(self.config['selectors']['loaded_indicator'], state='visible', timeout=15000)
             logger.info("UI Loaded.")
        except Exception:
             logger.warning("UI load timeout - proceeding anyway.")

    async def get_balance(self) -> float:
        """Reads balance from the UI header."""
        selector = self.config['selectors'].get('balance_text')
        if not selector: return 0.0

        try:
            text = await self._get_text(selector)
            # Remove '$', ',', 'USDT' etc
            clean_text = text.replace('$','').replace(',','').replace('USDT','').strip()
            return float(clean_text)
        except Exception as e:
            logger.warning(f"Failed to parse balance: {e}")
            return 0.0

    async def get_orderbook_price(self, symbol: str) -> Tuple[float, float]:
        """
        Reads the mid-price or mark-price from the UI.
        UI often doesn't show bid/ask explicitly, just 'Current Price'.
        """
        selector = self.config['selectors'].get('price_text')
        if not selector: return 0.0, 0.0

        try:
            text = await self._get_text(selector)
            price = float(text.replace(',','').strip())
            # Simulate a spread if UI only gives one price
            return price * 0.9995, price * 1.0005
        except Exception:
            return 0.0, 0.0

    async def create_market_order(self, 
                                symbol: str, 
                                side: str, 
                                size: float, 
                                price_limit: float = None,
                                params: Dict = None) -> Dict:
        """
        Simulates:
        1. Clicking 'Market' tab
        2. Entering Size
        3. Clicking Buy/Sell button
        """
        s = self.config['selectors']
        
        try:
            # 1. Ensure we are on Market tab
            if s.get('market_tab'):
                await self.page.click(s['market_tab'])
            
            # 2. Input Size
            await self._click_and_type(s['size_input'], str(size))
            
            # 3. Click Buy or Sell
            btn_selector = s['buy_btn'] if side.lower() == 'buy' else s['sell_btn']
            await self.page.click(btn_selector)
            
            # 4. Wait for confirmation toast/modal
            # This is optimistic. Real implementation needs robust checks.
            # await self.page.wait_for_selector(s['success_toast'])
            
            return {'success': True, 'tx_hash': 'ui-interaction-complete'}
            
        except Exception as e:
            logger.error(f"Browser Trade Failed: {e}")
            # Screenshot for debugging
            await self.page.screenshot(path=f"error_{side}_{size}.png")
            return {'success': False, 'error': str(e)}

    async def set_leverage(self, symbol: str, leverage: int, margin_mode: str) -> bool:
        # Complex UI interaction often required (Click slider, drag handle, or type)
        # Placeholder
        return True
    
    async def get_market_precision(self, symbol: str) -> int:
        return 4
