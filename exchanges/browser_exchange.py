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
            
            # 1. Prepare Proxy Config (Split Server vs Credentials)
            launch_proxy = None
            http_credentials = None

            if self.proxy_url:
                from urllib.parse import urlparse
                parsed = urlparse(self.proxy_url)
                
                # Server is always required for launch
                server_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
                launch_proxy = {"server": server_url}

                # Credentials go to context/http_credentials
                if parsed.username and parsed.password:
                    http_credentials = {
                        "username": parsed.username,
                        "password": parsed.password
                    }

            # 2. Prepare Launch Args
            # Add Linux stability args
            stability_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--no-sandbox", 
                "--disable-dev-shm-usage",
                "--disable-features=VizDisplayCompositor"
            ]

            common_args = {
                "headless": self.headless,
                "args": stability_args,
            }

            if launch_proxy:
                common_args["proxy"] = launch_proxy

            # 3. Launch Browser
            if self.user_data_dir:
                # Persistent Context: http_credentials goes directly here
                if http_credentials:
                    common_args["http_credentials"] = http_credentials
                    
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    **common_args
                )
            else:
                # Non-Persistent: Launch -> New Context (with credentials)
                self.browser = await self.playwright.chromium.launch(**common_args)
                
                context_args = {}
                if http_credentials:
                    context_args["http_credentials"] = http_credentials
                    
                self.context = await self.browser.new_context(**context_args)

            self.page = await self.context.new_page() if not self.user_data_dir else self.context.pages[0]
            
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
