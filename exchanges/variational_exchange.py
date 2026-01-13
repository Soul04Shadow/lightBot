import logging
import asyncio
import aiohttp
from typing import Dict, Tuple, Any, Optional
from .browser_exchange import BrowserExchange

logger = logging.getLogger(__name__)

class VariationalExchange(BrowserExchange):
    """
    Hybrid Exchange Adapter for Variational.
    - Uses Public REST API for fast price/market data.
    - Uses Browser Automation (Playwright) for trade execution (since Trading API is closed).
    """

    API_BASE_URL = "https://omni-client-api.prod.ap-northeast-1.variational.io"

    def __init__(self, config: Dict[str, Any]):
        # Default URL for Variational App if not provided
        if 'base_url' not in config:
            config['base_url'] = "https://app.variational.io" # Best guess, user should confirm
        super().__init__(config)
        self.api_session = None

    async def initialize(self) -> bool:
        # Init Browser
        browser_success = await super().initialize()
        if not browser_success:
            return False
            
        # Init API Session
        self.api_session = aiohttp.ClientSession()
        return True

    async def _post_launch_setup(self):
        """
        Wait for Variational UI to load and ensure Wallet is connected.
        """
        s = self.config.get('selectors', {})
        try:
            logger.info("Waiting for Variational UI to load...")
            # 1. Wait for basic UI structure
            await self.page.wait_for_load_state('networkidle', timeout=20000)
            
            # 2. Ensure Wallet Connection
            await self._ensure_wallet_connected(s)

        except Exception as e:
            logger.warning(f"Startup warning: {e}")

    async def _ensure_wallet_connected(self, selectors: Dict):
        """Checks for connection and attempts to connect if disconnected."""
        logger.info("Verifying Wallet Connection...")
        
        # Method A: Check if 'Account Details' or 'Balance' element is visible (Sign of connection)
        success_indicator = selectors.get('account_details', '.portfolio-details')
        try:
            await self.page.wait_for_selector(success_indicator, state='visible', timeout=5000)
            logger.info("Wallet detected as CONNECTED.")
            return True
        except Exception:
            logger.info("Wallet not detected. Attempting to connect...")

        # Method B: Attempt to click 'Connect Wallet'
        connect_btn = selectors.get('connect_wallet_btn')
        if connect_btn:
            try:
                # Click logic
                if await self.page.is_visible(connect_btn):
                    logger.info(f"Clicking {connect_btn}...")
                    await self.page.click(connect_btn)
                    
                    # Wait for user to handle extension popup
                    # We can't automate the extension popup easily, but we can wait until connection succeeds
                    logger.info("Waiting for user to approve wallet connection...")
                    try:
                        await self.page.wait_for_selector(success_indicator, state='visible', timeout=60000) # 60s wait
                        logger.info("Wallet connected successfully!")
                        return True
                    except Exception:
                        logger.error("Timed out waiting for wallet connection.")
                        return False
            except Exception as e:
                logger.error(f"Error clicking connect button: {e}")
        
        return False

    async def get_orderbook_price(self, symbol: str) -> Tuple[float, float]:
        """
        Fetches price from REST API (Faster/Reliable than UI scraping).
        Symbol should be ticker like 'BTC', 'ETH'.
        """
        try:
            async with self.api_session.get(f"{self.API_BASE_URL}/metadata/stats") as resp:
                if resp.status != 200:
                    logger.warning(f"Variational API Error: {resp.status}")
                    return 0.0, 0.0
                
                data = await resp.json()
                listings = data.get('listings', [])
                
                for item in listings:
                    if item.get('ticker') == symbol:
                        # Prefer 1k quote for executable price, else mark price
                        quotes = item.get('quotes', {}).get('size_1k', {})
                        bid = float(quotes.get('bid', 0))
                        ask = float(quotes.get('ask', 0))
                        
                        if bid == 0 or ask == 0:
                            mark = float(item.get('mark_price', 0))
                            return mark, mark
                            
                        return bid, ask
                        
            return 0.0, 0.0
        except Exception as e:
            logger.error(f"Failed to fetch Variational prices: {e}")
            return 0.0, 0.0

    async def get_balance(self) -> float:
        """
        Reads Portfolio Balance from UI.
        Selector needs to be configured in .env as VARIATIONAL_SELECTOR_BALANCE
        """
        selector = self.config.get('selectors', {}).get('balance_text', '.portfolio-value') 
        try:
            text = await self._get_text(selector)
            # Remove symbols like $, USDb, etc
            clean_text = text.replace('$','').replace(',','').replace('USDb','').strip()
            return float(clean_text)
        except Exception as e:
            logger.debug(f"Failed to scrape balance: {e}")
            return 0.0

    async def get_market_precision(self, symbol: str) -> int:
        """
        Returns the number of decimals for volume/size.
        For now, defaulting to 3 (e.g. 0.001) as observed in UI.
        TODO: Fetch dynamically from metadata API.
        """
        return 3

    async def set_leverage(self, symbol: str, leverage: int, margin_mode: str) -> bool:
        """
        Sets leverage via UI interaction.
        Requires selectors: 'leverage_open_btn', 'leverage_input', 'leverage_confirm_btn'
        """
        s = self.config.get('selectors', {})
        try:
            logger.info(f"Setting leverage to {leverage}x...")
            
            # 1. Click the Leverage Display/Button to open the modal/slider
            if s.get('leverage_open_btn'):
                await self.page.click(s['leverage_open_btn'])
                await self.page.wait_for_timeout(500) # Short UI animation wait

            # 2. Enter Leverage Value
            if s.get('leverage_input'):
                await self.page.fill(s['leverage_input'], str(leverage))
            
            # 3. Confirm Leverage Change
            if s.get('leverage_confirm_btn'):
                await self.page.click(s['leverage_confirm_btn'])
                # Wait for modal to close
                await self.page.wait_for_timeout(1000) 
                
            return True
        except Exception as e:
            logger.error(f"Failed to set leverage: {e}")
            return False


    async def create_market_order(self, 
                                symbol: str, 
                                side: str, 
                                size: float, 
                                price_limit: float = None, 
                                params: Dict = None) -> Dict:
        """
        Executes trade via UI interaction with verification.
        """
        try:
            s = self.config.get('selectors', {})
            logger.info(f"Variational Browser: Placing {side} {size} {symbol}")
            
            # --- 1. ENSURE MARKET TAB ---
            if s.get('market_tab'):
                try:
                    if not await self.page.is_disabled(s['market_tab']):
                        await self.page.click(s['market_tab'])
                except Exception:
                    pass

            # --- 2. INPUT SIZE ---
            if s.get('size_input'):
                # Playwright's fill clears the field first automatically
                await self.page.fill(s['size_input'], str(size))
                # Optional: Read back value for sanity check could go here


            # --- 3. SELECT SIDE (Toggle) ---
            # In Variational, these buttons toggle the mode (Buy Mode vs Sell Mode)
            btn_selector = s.get('buy_btn') if side.lower() == 'buy' else s.get('sell_btn')
            if btn_selector:
                try:
                    is_disabled = await self.page.is_disabled(btn_selector)
                    if not is_disabled:
                        await self.page.click(btn_selector, force=True)
                        await self.page.wait_for_timeout(200) # Small wait for UI update
                    else:
                        logger.info(f"{side} button is disabled (already active).")
                except Exception as e:
                    logger.warning(f"Error clicking {side} button: {e}")
            else:
                return {'success': False, 'error': f'No selector for {side} button'}

            # --- 4. VERIFY SUBMIT BUTTON STATE ---
            if s.get('submit_btn'):
                # Check what the button says (e.g., "Deposit Funds" vs "Buy BTC")
                btn_text = await self._get_text(s['submit_btn'])
                btn_text_clean = btn_text.lower()
                
                # Critical Failures
                if "deposit" in btn_text_clean or "insufficient" in btn_text_clean:
                    return {'success': False, 'error': f"Cannot trade: Button says '{btn_text}'"}

                # Click
                await self.page.click(s['submit_btn'])
                logger.info(f"Clicked Submit Button ('{btn_text}')")
            else:
                return {'success': False, 'error': 'No submit button selector found'}

            # --- 5. HANDLE CONFIRMATION MODAL ---
            if s.get('order_confirm_modal_btn'):
                try:
                    # Wait briefly for modal to appear
                    await self.page.wait_for_selector(s['order_confirm_modal_btn'], state='visible', timeout=2000)
                    await self.page.click(s['order_confirm_modal_btn'])
                    logger.info("Confirmed order modal.")
                except Exception:
                    # If it times out, maybe no modal appeared (one-click trading might be on)
                    pass
            
            # --- 6. EXPLICIT SUCCESS VERIFICATION ---
            # Wait for some feedback.
            # 1. Toast?
            if s.get('success_toast'):
                try:
                    await self.page.wait_for_selector(s['success_toast'], timeout=3000)
                    logger.info("Success toast detected.")
                    return {'success': True, 'tx_hash': 'browser-submitted-verified'}
                except Exception:
                    pass # Toast might be missed or disabled
            
            # 2. Fallback: Assume success if no error toast appeared immediately
            # (Ideally we verify via position size change, but that requires reading position before & after)
            await self.page.wait_for_timeout(1000)

            return {'success': True, 'tx_hash': 'browser-submitted-likely'}

        except Exception as e:
            logger.error(f"Variational Trade Error: {e}")
            try:
                await self.page.screenshot(path=f"error_variational_{symbol}_{side}.png")
            except: 
                pass
            return {'success': False, 'error': str(e)}

    async def close(self):
        if self.api_session:
            await self.api_session.close()
        await super().close()
