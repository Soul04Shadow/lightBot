from abc import abstractmethod
import asyncio
from typing import Optional, Dict, Tuple, Any
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from .base import ExchangeClient
import logging

logger = logging.getLogger(__name__)

class BrowserExchange(ExchangeClient):
    """
    Base class for exchanges that require Browser Automation (no API).
    Implements the ExchangeClient interface using Playwright.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.url = config.get('base_url')
        self.headless = config.get('headless', False) # Default to visible for debugging
        self.user_data_dir = config.get('user_data_dir', None) # For persistent logins
        self.proxy_url = config.get('proxy', None)

    async def initialize(self) -> bool:
        """Launches the browser and navigates to the exchange."""
        try:
            self.playwright = await async_playwright().start()
            
            # Proxy Configuration
            proxy_settings = None
            if self.proxy_url:
                from urllib.parse import urlparse
                parsed = urlparse(self.proxy_url)
                
                # Extract credentials if present in URL
                if parsed.username and parsed.password:
                    proxy_settings = {
                        "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
                        "username": parsed.username,
                        "password": parsed.password
                    }
                else:
                    proxy_settings = {"server": self.proxy_url}

            launch_args = {
                "headless": self.headless,
                "args": ["--disable-blink-features=AutomationControlled"], # Basic stealth
            }
            
            # NOTE: When using launch_persistent_context, proxy MUST be passed in launch_args
            if self.user_data_dir:
                if proxy_settings:
                    launch_args["proxy"] = proxy_settings
                    
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    **launch_args
                )
            else:
                # For non-persistent, we pass proxy to launch() AND new_context() 
                # passing it to launch() avoids the 'proxy login' popup in visible mode
                if proxy_settings:
                    launch_args["proxy"] = proxy_settings
                    
                self.browser = await self.playwright.chromium.launch(**launch_args)
                self.context = await self.browser.new_context() # Proxy already inherited from launch

            self.page = await self.context.new_page()
            
            logger.info(f"Navigating to {self.url}...")
            await self.page.goto(self.url)
            
            # Allow implementation-specific login/setup
            await self._post_launch_setup()
            
            return True
        except Exception as e:
            logger.error(f"Browser Init Failed: {e}")
            return False

    @abstractmethod
    async def _post_launch_setup(self):
        """
        Handle login, wallet connection, or popups here.
        Must be implemented by specific exchange adapter.
        """
        pass

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    # --- Wrapper helpers for safe DOM interaction ---

    async def _get_text(self, selector: str) -> str:
        try:
            return await self.page.inner_text(selector, timeout=5000)
        except Exception:
            return ""

    async def _click_and_type(self, selector: str, text: str):
        await self.page.click(selector)
        await self.page.fill(selector, text)
