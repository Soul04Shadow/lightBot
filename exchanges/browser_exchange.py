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
                try:
                    # Handle "host:port:username:password" format (common in proxy lists)
                    # We define a helper to safely parse this without relying solely on urlparse's strict port integers
                    proxy_str = self.proxy_url.strip()
                    if "://" not in proxy_str:
                        proxy_str = f"http://{proxy_str}"
                    
                    from urllib.parse import urlparse
                    parsed = urlparse(proxy_str)
                    
                    # Check if we have the "host:port:user:pass" structure in the netloc
                    # This often manifests as a ValueError when accessing parsed.port, or we can detect it by splitting
                    netloc_parts = parsed.netloc.split(':')
                    
                    if len(netloc_parts) == 4:
                        # Format: host:port:username:password
                        server_url = f"{parsed.scheme}://{netloc_parts[0]}:{netloc_parts[1]}"
                        http_credentials = {
                            "username": netloc_parts[2],
                            "password": netloc_parts[3]
                        }
                    else:
                        # Standard format: http://user:pass@host:port or http://host:port
                        # We use parsed properties. Accessing parsed.port might raise ValueError if malformed,
                        # but standard format should work.
                        server_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
                        if parsed.username and parsed.password:
                            http_credentials = {
                                "username": parsed.username,
                                "password": parsed.password
                            }
                            
                    launch_proxy = {"server": server_url}
                    
                except Exception as e:
                    logger.error(f"Failed to parse proxy URL '{self.proxy_url}': {e}")
                    raise

            # 2. Prepare Launch Args
            # Add Linux stability args & Stealth args
            stability_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--no-sandbox", 
                "--disable-dev-shm-usage",
                "--disable-features=VizDisplayCompositor",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized"
            ]

            # Use a fixed, real User-Agent to prevent 'Headless' detection
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

            common_args = {
                "headless": self.headless,
                "args": stability_args,
                "user_agent": user_agent,
                "viewport": {"width": 1920, "height": 1080},
                "ignore_default_args": ["--enable-automation"],
                "channel": "chrome" # Try to use installed Chrome if available for better stealth
            }

            if launch_proxy:
                common_args["proxy"] = launch_proxy

            # 3. Launch Browser
            if self.user_data_dir:
                # Persistent Context: http_credentials goes directly here
                if http_credentials:
                    common_args["http_credentials"] = http_credentials
                
                try:
                    self.context = await self.playwright.chromium.launch_persistent_context(
                        user_data_dir=self.user_data_dir,
                        **common_args
                    )
                except Exception as e:
                    # Fallback: Try without 'channel' (use bundled Chromium)
                    if "channel" in common_args:
                        logger.warning(f"Launch with channel='chrome' failed ({e}). Retrying with bundled Chromium...")
                        del common_args["channel"]
                        self.context = await self.playwright.chromium.launch_persistent_context(
                            user_data_dir=self.user_data_dir,
                            **common_args
                        )
                    else:
                        raise e
            else:
                # Non-Persistent: Launch -> New Context (with credentials)
                # Note: launch() doesn't take user_agent/viewport, new_context() does.
                
                # Filter args for direct launch
                launch_keys = ['headless', 'args', 'proxy', 'channel', 'ignore_default_args']
                launch_args = {k: v for k, v in common_args.items() if k in launch_keys}
                
                try:
                    self.browser = await self.playwright.chromium.launch(**launch_args)
                except Exception as e:
                    if "channel" in launch_args:
                        logger.warning(f"Launch with channel='chrome' failed. Retrying with bundled Chromium...")
                        del launch_args["channel"]
                        self.browser = await self.playwright.chromium.launch(**launch_args)
                    else:
                        raise e
                
                context_args = {
                    "user_agent": user_agent,
                    "viewport": {"width": 1920, "height": 1080}
                }
                if http_credentials:
                    context_args["http_credentials"] = http_credentials
                    
                self.context = await self.browser.new_context(**context_args)

            # STEALTH: Apply script to mask webdriver property
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

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
