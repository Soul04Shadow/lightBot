"""
API Adapter Factory

Factory for creating and managing API adapters for different DEX platforms.
"""

import logging
from typing import Dict, Any, Optional, Type

from api_adapter_base import APIAdapterBase
from adapters.lighter_adapter import LighterAdapter

logger = logging.getLogger(__name__)


class AdapterFactory:
    """Factory for creating API adapter instances"""
    
    # Registry of available adapters
    _adapters: Dict[str, Type[APIAdapterBase]] = {
        'lighter': LighterAdapter,
        # Add more adapters here as they are implemented:
        # 'paradex': ParadexAdapter,
        # 'dydx': DydxAdapter,
        # 'hyperliquid': HyperliquidAdapter,
    }
    
    @classmethod
    def register_adapter(cls, name: str, adapter_class: Type[APIAdapterBase]) -> None:
        """
        Register a new adapter type.
        
        Args:
            name: Adapter identifier (e.g., 'lighter', 'paradex')
            adapter_class: Adapter class that inherits from APIAdapterBase
        """
        cls._adapters[name.lower()] = adapter_class
        logger.info("Registered adapter: %s", name)
    
    @classmethod
    def get_available_adapters(cls) -> list[str]:
        """
        Get list of available adapter names.
        
        Returns:
            List of registered adapter names
        """
        return list(cls._adapters.keys())
    
    @classmethod
    def create_adapter(
        cls,
        adapter_name: str,
        config: Dict[str, Any]
    ) -> APIAdapterBase:
        """
        Create an adapter instance.
        
        Args:
            adapter_name: Name of the adapter to create (e.g., 'lighter')
            config: Configuration dictionary for the adapter
            
        Returns:
            Initialized adapter instance
            
        Raises:
            ValueError: If adapter name is not registered
            Exception: If adapter configuration is invalid
        """
        adapter_name_lower = adapter_name.lower()
        
        if adapter_name_lower not in cls._adapters:
            available = ', '.join(cls.get_available_adapters())
            raise ValueError(
                f"Unknown adapter: '{adapter_name}'. "
                f"Available adapters: {available}"
            )
        
        adapter_class = cls._adapters[adapter_name_lower]
        
        # Validate configuration
        adapter_instance = adapter_class(config)
        is_valid, error_msg = adapter_instance.validate_config(config)
        
        if not is_valid:
            raise ValueError(
                f"Invalid configuration for {adapter_name} adapter: {error_msg}"
            )
        
        logger.info("Created %s adapter instance", adapter_name)
        return adapter_instance
    
    @classmethod
    def create_worker_adapter(
        cls,
        adapter_name: str,
        account_config: Dict[str, Any]
    ) -> APIAdapterBase:
        """
        Create an adapter for use in a worker process.
        
        Args:
            adapter_name: Name of the adapter
            account_config: Account-specific configuration
            
        Returns:
            Adapter instance configured for single account
        """
        return cls.create_adapter(adapter_name, account_config)


class AdapterManager:
    """
    Manages multiple adapter instances for orchestrated trading.
    
    This handles creating and coordinating adapters for multiple accounts
    while maintaining the isolation needed to prevent signer conflicts.
    """
    
    def __init__(self, adapter_name: str):
        """
        Initialize adapter manager.
        
        Args:
            adapter_name: Name of the adapter to use for all accounts
        """
        self.adapter_name = adapter_name
        self._adapters: Dict[str, APIAdapterBase] = {}
    
    def create_account_adapter(
        self,
        account_id: str,
        account_config: Dict[str, Any]
    ) -> APIAdapterBase:
        """
        Create and register an adapter for a specific account.
        
        Args:
            account_id: Unique identifier for this account (e.g., 'account1', 'account2')
            account_config: Configuration for this account
            
        Returns:
            Created adapter instance
        """
        adapter = AdapterFactory.create_adapter(self.adapter_name, account_config)
        self._adapters[account_id] = adapter
        logger.info("Created adapter for account: %s", account_id)
        return adapter
    
    def get_adapter(self, account_id: str) -> Optional[APIAdapterBase]:
        """
        Get adapter for a specific account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Adapter instance or None if not found
        """
        return self._adapters.get(account_id)
    
    async def initialize_all(self) -> bool:
        """
        Initialize all registered adapters.
        
        Returns:
            True if all adapters initialized successfully
        """
        success = True
        for account_id, adapter in self._adapters.items():
            if not await adapter.initialize():
                logger.error("Failed to initialize adapter for account: %s", account_id)
                success = False
        return success
    
    async def close_all(self) -> None:
        """Close all adapter connections"""
        for account_id, adapter in self._adapters.items():
            try:
                await adapter.close()
                logger.info("Closed adapter for account: %s", account_id)
            except Exception as e:
                logger.error("Error closing adapter for %s: %s", account_id, e)
    
    def get_adapter_info(self) -> Dict[str, Any]:
        """
        Get information about managed adapters.
        
        Returns:
            Dictionary with adapter information
        """
        return {
            'adapter_name': self.adapter_name,
            'account_count': len(self._adapters),
            'accounts': list(self._adapters.keys()),
        }
