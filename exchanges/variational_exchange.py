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
        
        # Verify Connection/Setup
        if not await self._post_launch_setup():
            logger.error("Initialization Failed: Wallet not connected.")
            await self.close()
            return False
            
        return True

    async def _post_launch_setup(self) -> bool:
        """
        Wait for Variational UI to load and ensure Wallet is connected.
        Returns: True if connected and ready, False otherwise.
        """
        s = self.config.get('selectors', {})
        try:
            logger.info("Waiting for Variational UI to load...")
            
            # 0. Check for Captcha / Cloudflare
            await self._handle_captcha()

            # 1. Wait for basic UI structure
            await self.page.wait_for_load_state('networkidle', timeout=20000)
            
            # 2. Ensure Wallet Connection
            connected = await self._ensure_wallet_connected(s)
            return connected

        except Exception as e:
            logger.warning(f"Startup warning: {e}")
            return False

    async def _handle_captcha(self):
        """Checks for Cloudflare/Captcha and pauses/notifies if detected."""
        try:
            # Common patterns for Cloudflare or generic captchas
            captcha_selectors = [
                 "iframe[title*='Cloudflare']",
                 "div:has-text('Verify you are human')",
                 "div:has-text('Checking if the site connection is secure')"
            ]
            
            for _ in range(3): # Quick checks
                found = False
                for sel in captcha_selectors:
                    if await self.page.is_visible(sel):
                        found = True
                        break
                
                if found:
                    logger.warning("CAPTCHA DETECTED! Waiting up to 2 minutes for resolution...")
                    # Wait loop
                    for w in range(24): # 2 mins (24 * 5s)
                        await asyncio.sleep(5)
                        # Check if gone
                        still_there = False
                        for sel in captcha_selectors:
                            if await self.page.is_visible(sel):
                                still_there = True
                                break
                        if not still_there:
                            logger.info("Captcha appears to be resolved.")
                            return
                    logger.error("Captcha timed out. Manual intervention required.")
                    return

                await asyncio.sleep(1)
        except Exception as e:
            logger.debug(f"Error checking captcha: {e}")

    async def _ensure_wallet_connected(self, selectors: Dict):
        """Checks for connection and attempts to connect if disconnected."""
        logger.info("Verifying Wallet Connection...")
        
        success_indicator = selectors.get('account_details', '.portfolio-details')
        connect_btn = selectors.get('connect_wallet_btn', "button:has-text('Connect Wallet')")

        # Retry loop for initial connection - giving ample time for user interaction
        max_duration = 300 # 5 minutes
        poll_interval = 5
        
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < max_duration:
            # 1. Check if definitely DISCONNECTED (Connect button visible)
            is_disconnected = False
            try:
                if await self.page.is_visible(connect_btn):
                    is_disconnected = True
                    # Only click it once or if it reappears distinctively?
                    # Better to let the user do it if headless=False, or click it if we can.
                    # We'll click it once per loop iteration if it's there, 
                    # but only if we haven't clicked it recently to avoid spamming.
                    
                    # If headless=True, we MUST click it.
                    # If headless=False, user might do it.
                    # Let's try to click it automatically.
                    logger.info("Connect Wallet button visible. Clicking...")
                    await self.page.click(connect_btn)
                    await asyncio.sleep(2) # Wait for modal
            except Exception:
                pass

            # 2. Check if CONNECTED (Success indicator visible AND Connect button NOT visible)
            try:
                connected = await self.page.is_visible(success_indicator)
                btn_visible = await self.page.is_visible(connect_btn)
                
                if connected and not btn_visible:
                    # Double check balance isn't empty/loading?
                    # For now, this is a strong signal of connection.
                    logger.info("Wallet detected as CONNECTED.")
                    return True
            except Exception:
                pass
            
            # 3. Wait and Log
            elapsed = int(asyncio.get_event_loop().time() - start_time)
            if elapsed % 15 == 0:
                logger.info(f"Waiting for wallet connection... ({elapsed}s elapsed)")
            
            await asyncio.sleep(poll_interval)
            
        logger.error("Failed to establish wallet connection after waiting.")
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
        
        # Retry logic for reading balance (sometimes it loads as 0 momentarily)
        for _ in range(3):
            try:
                text = await self._get_text(selector)
                # Remove symbols like $, USDb, etc
                clean_text = text.replace('$','').replace(',','').replace('USDb','').strip()
                val = float(clean_text)
                if val > 0:
                    return val
            except Exception as e:
                logger.debug(f"Failed to scrape balance: {e}")
            
            await asyncio.sleep(1)
            
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
