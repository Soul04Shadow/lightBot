#!/usr/bin/env python3
"""
Adapter-Agnostic Account Worker

Runs as a separate process to execute trades for a single account.
This version uses the adapter pattern to support multiple DEX platforms.
"""

import asyncio
import json
import logging
import sys
from typing import Optional, Tuple

from dotenv import load_dotenv

from adapter_factory import AdapterFactory
from api_adapter_base import APIAdapterBase

logger = logging.getLogger(__name__)

load_dotenv()


class AdapterAccountWorker:
    """Manages a single trading account using an API adapter"""
    
    def __init__(self, adapter: APIAdapterBase):
        """
        Initialize worker with an API adapter.
        
        Args:
            adapter: API adapter instance for this account
        """
        self.adapter = adapter
        
    async def initialize(self) -> bool:
        """
        Initialize the API adapter.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.adapter.initialize()
        except Exception as e:
            print(f"Error initializing worker: {e}", file=sys.stderr)
            return False
    
    async def update_leverage(
        self, market_index: int, leverage: int, margin_mode: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Update leverage settings for the account.
        
        Args:
            market_index: Market ID
            leverage: Leverage multiplier
            margin_mode: 0 for cross, 1 for isolated
            
        Returns:
            Tuple of (success flag, optional error message)
        """
        try:
            return await self.adapter.update_leverage(
                market_id=market_index,
                leverage=leverage,
                margin_mode=margin_mode
            )
        except Exception as e:
            error_msg = f"Failed to update leverage: {e}"
            print(error_msg, file=sys.stderr)
            return False, error_msg
    
    async def execute_true_market_order(self, order_params: dict) -> dict:
        """
        Execute a market order with worst-case price limit.
        
        Args:
            order_params: Order parameters including market_index, base_amount,
                         execution_price, is_ask, and optional reduce_only
                         
        Returns:
            Dictionary with success status, tx_hash or error message
        """
        try:
            result = await self.adapter.create_market_order(
                market_id=order_params['market_index'],
                base_amount=order_params['base_amount'],
                is_ask=order_params['is_ask'],
                execution_price=order_params['execution_price'],
                reduce_only=order_params.get('reduce_only', False),
                client_order_id=order_params.get('client_order_index')
            )

            if result.success:
                return {'success': True, 'tx_hash': result.tx_hash}
            else:
                return {'success': False, 'error': result.error}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def close(self):
        """Close the adapter connection and cleanup resources"""
        await self.adapter.close()


async def main():
    """
    Main worker process entry point.
    Reads configuration from stdin, executes command, outputs result to stdout.
    """
    config_json = sys.stdin.read()
    config = json.loads(config_json)
    
    # Get adapter name and account config
    adapter_name = config.get('api_adapter', 'lighter')
    account_config = config['account']
    
    # Create adapter instance
    try:
        adapter = AdapterFactory.create_worker_adapter(adapter_name, account_config)
    except Exception as e:
        result = {'success': False, 'error': f'Failed to create adapter: {e}'}
        print(json.dumps(result))
        sys.exit(1)
    
    worker = AdapterAccountWorker(adapter)
    
    if not await worker.initialize():
        result = {'success': False, 'error': 'Failed to initialize worker'}
        print(json.dumps(result))
        sys.exit(1)
    
    try:
        command = config.get('command')
        
        if command == 'update_leverage':
            leverage_params = config['leverage']
            success, error = await worker.update_leverage(
                leverage_params['market_index'],
                leverage_params['leverage'],
                leverage_params['margin_mode']
            )
            result = {'success': success}
            if error:
                result['error'] = error
                
        elif command == 'execute_true_market_order':
            result = await worker.execute_true_market_order(config['order'])
            
        else:
            result = {'success': False, 'error': f'Unknown command: {command}'}
        
        print(json.dumps(result))
        
    finally:
        await worker.close()


if __name__ == '__main__':
    asyncio.run(main())
