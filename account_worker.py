#!/usr/bin/env python3
"""
Generic Isolated Account Worker

Runs as a separate process to execute trades for a single account.
This isolation prevents signer conflicts when managing multiple accounts.
Now supports multiple exchanges via the ExchangeClient interface.
"""

import asyncio
import json
import logging
import sys
import os
import traceback
from typing import Optional, Tuple

from dotenv import load_dotenv

# Ensure we can import from local packages
sys.path.append(os.getcwd())

# Import our new Exchange abstractions
try:
    from exchanges.lighter_exchange import LighterExchange
    from exchanges.generic_browser_dex import GenericBrowserDex
    from exchanges.variational_exchange import VariationalExchange
except ImportError:
    # Fallback if running from a different context
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from exchanges.lighter_exchange import LighterExchange
    from exchanges.generic_browser_dex import GenericBrowserDex
    from exchanges.variational_exchange import VariationalExchange

logger = logging.getLogger(__name__)

load_dotenv()

class WorkerFactory:
    @staticmethod
    def create_exchange(config: dict):
        exchange_type = config.get('exchange_type', 'lighter')
        
        if exchange_type == 'lighter':
            return LighterExchange(config)
        elif exchange_type == 'browser':
            return GenericBrowserDex(config)
        elif exchange_type == 'variational':
            return VariationalExchange(config)
        else:
            raise ValueError(f"Unknown exchange type: {exchange_type}")

async def main():
    """
    Main worker process entry point.
    Reads configuration from stdin, executes command, outputs result to stdout.
    """
    try:
        # 1. Read Input
        config_json = sys.stdin.read()
        if not config_json:
             print(json.dumps({'success': False, 'error': 'No input received'}))
             return

        config = json.loads(config_json)
        
        # 2. Setup Exchange
        account_config = config['account']
        # Ensure exchange_type is passed, default to lighter for backward compatibility
        if 'exchange_type' not in account_config:
            account_config['exchange_type'] = 'lighter'
            
        exchange = WorkerFactory.create_exchange(account_config)
        
        if not await exchange.initialize():
            print(json.dumps({'success': False, 'error': 'Failed to initialize exchange connection'}))
            return

        # 3. Execute Command
        command = config.get('command')
        result = {'success': False, 'error': 'Unknown command'}

        if command == 'update_leverage':
            args = config.get('leverage', {})
            success = await exchange.set_leverage(
                symbol=str(args.get('market_index', '')),
                leverage=args.get('leverage'),
                margin_mode='isolated' if args.get('margin_mode') == 1 else 'cross'
            )
            if success:
                result = {'success': True, 'message': 'Leverage updated'}
            else:
                result = {'success': False, 'error': 'Failed to verify leverage update'}
        
        elif command == 'execute_true_market_order':
            # Mapping old param structure to new interface
            order_params = config['order']
            
            # Translate params
            symbol = str(order_params['market_index'])
            side = 'sell' if order_params['is_ask'] else 'buy'
            size = order_params['base_amount']
            price_limit = order_params.get('execution_price')
            
            # Pass through other params
            extra_params = {
                'client_order_index': order_params.get('client_order_index'),
                'reduce_only': order_params.get('reduce_only', False)
            }
            
            result = await exchange.create_market_order(
                symbol=symbol,
                side=side,
                size=size,
                price_limit=price_limit,
                params=extra_params
            )
            
        else:
            result = {'success': False, 'error': f'Unknown command: {command}'}

        # 4. Cleanup and Output
        await exchange.close()
        print(json.dumps(result))

    except Exception as e:
        # Catch-all to ensure we always print valid JSON to stdout
        tb = traceback.format_exc()
        print(json.dumps({'success': False, 'error': f'Worker Crash: {str(e)}', 'traceback': tb}))
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())