#!/usr/bin/env python3
"""
Isolated Account Worker

Runs as a separate process to execute trades for a single account.
This isolation prevents signer conflicts when managing multiple accounts.
"""

import asyncio
import json
import logging
import sys
from typing import Optional, Tuple

from dotenv import load_dotenv

import lighter

logger = logging.getLogger(__name__)

load_dotenv()


class SingleAccountWorker:
    """Manages a single trading account in an isolated process"""
    
    def __init__(self, account_config: dict):
        self.config = account_config
        self.client = None
        self._last_leverage_request: Optional[Tuple[int, int, int]] = None
        
    async def initialize(self) -> bool:
        """
        Initialize the Lighter SignerClient for this account.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client = lighter.SignerClient(
                url=self.config['base_url'],
                private_key=self.config['private_key'],
                account_index=self.config['account_index'],
                api_key_index=self.config['api_key_index'],
            )
            return True
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
            last_request = self._last_leverage_request
            current_request = (market_index, leverage, margin_mode)

            if last_request == current_request:
                logger.info(
                    "Skipping leverage update for market %s: leverage=%s margin_mode=%s unchanged",
                    market_index,
                    leverage,
                    margin_mode,
                )
                return True, None

            await self.client.update_leverage(
                market_index=market_index,
                margin_mode=margin_mode,
                leverage=leverage
            )

            self._last_leverage_request = current_request
            logger.info(
                "Updated leverage for market %s: leverage=%s margin_mode=%s",
                market_index,
                leverage,
                margin_mode,
            )
            return True, None
        except Exception as e:
            print(f"Warning: Could not update leverage: {e}", file=sys.stderr)
            return False, str(e)
    
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
            result = await self.client.create_market_order(
                market_index=order_params['market_index'],
                client_order_index=order_params['client_order_index'],
                base_amount=order_params['base_amount'],
                avg_execution_price=order_params['execution_price'],
                is_ask=order_params['is_ask'],
                reduce_only=order_params.get('reduce_only', False)
            )

            create_order, resp, error = result

            if error:
                return {'success': False, 'error': error}

            if resp and resp.code == 200:
                return {'success': True, 'tx_hash': resp.tx_hash}
            
            error_msg = f"API Error {resp.code if resp else 'N/A'}"
            if resp and resp.message:
                error_msg += f": {resp.message}"
            return {'success': False, 'error': error_msg}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def close(self):
        """Close the client connection and cleanup resources"""
        if self.client:
            await self.client.close()


async def main():
    """
    Main worker process entry point.
    Reads configuration from stdin, executes command, outputs result to stdout.
    """
    config_json = sys.stdin.read()
    config = json.loads(config_json)
    
    worker = SingleAccountWorker(config['account'])
    
    if not await worker.initialize():
        result = {'success': False, 'error': 'Failed to initialize worker'}
        print(json.dumps(result))
        sys.exit(1)
    
    command = config.get('command')
    
    if command == 'update_leverage':
        success, error = await worker.update_leverage(
            market_index=config['leverage']['market_index'],
            leverage=config['leverage']['leverage'],
            margin_mode=config['leverage']['margin_mode']
        )
        if success:
            result = {'success': True, 'message': 'Leverage updated'}
        else:
            result = {
                'success': False,
                'error': error or 'Failed to update leverage'
            }
    elif command == 'execute_true_market_order':
        result = await worker.execute_true_market_order(config['order'])
    else:
        result = {'success': False, 'error': f'Unknown command: {command}'}
    
    print(json.dumps(result))
    await worker.close()


if __name__ == "__main__":
    asyncio.run(main())