"""
Delta Neutral Volume Generation Bot for Lighter DEX

Orchestrates delta-neutral trading by managing two isolated account workers.
Each worker handles a single account to prevent signer conflicts.
"""

import asyncio
import json
import logging
import random
import sys
from datetime import datetime
from typing import Optional, Tuple, Sequence, Any, Dict
from dotenv import load_dotenv
import lighter
from config import BotConfig

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('delta_neutral_bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class DeltaNeutralOrchestrator:
    """
    Orchestrates delta-neutral trading across two isolated account workers.
    
    Manages simultaneous long/short positions, position lifecycle, and
    ensures proper isolation between accounts to prevent signer conflicts.
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.trade_count = 0
        self.success_count = 0
        self.is_running = False
        self.open_positions = []
        self.close_retry_backoff_seconds = 5
        self.max_close_retries = 3
        self.close_failure_alert_active = False
        self.market_stats = {
            market_id: {
                'trades': 0,
                'successful': 0,
                'notional': 0.0,
                'volume_long': 0.0,
                'volume_short': 0.0,
                'bleed': 0.0,
            }
            for market_id in config.market_whitelist
        }
        self.total_notional = 0.0
        self.total_volume_long = 0.0
        self.total_volume_short = 0.0
        self.realized_bleed = 0.0
    
    def select_random_market(self) -> int:
        """Randomly select a market from the whitelist"""
        return random.choice(self.config.market_whitelist)

    def _validate_worker_results(self, results: Sequence[Any], context: str) -> None:
        """Validate results returned from worker commands."""
        errors = []

        for idx, result in enumerate(results, start=1):
            if isinstance(result, Exception):
                logger.error(
                    "Worker %s encountered an exception while attempting to %s: %s",
                    idx,
                    context,
                    result,
                )
                errors.append(f"worker {idx} exception: {result}")
            elif isinstance(result, dict) and not result.get('success', True):
                error_detail = result.get('error') or result
                logger.error(
                    "Worker %s reported failure while attempting to %s: %s",
                    idx,
                    context,
                    error_detail,
                )
                errors.append(f"worker {idx} failure: {error_detail}")

        if errors:
            raise RuntimeError(f"Failed to {context}: {'; '.join(errors)}")

    async def _fetch_account_balances(self) -> Tuple[Optional[float], Optional[float]]:
        """Fetch available balances for both accounts using the Lighter API."""
        try:
            async with self.config.api_client() as api_client:
                account_api = lighter.AccountApi(api_client)

                account1 = await account_api.account(
                    by="index",
                    value=str(self.config.account1_index),
                )
                account2 = await account_api.account(
                    by="index",
                    value=str(self.config.account2_index),
                )

                balance1 = None
                balance2 = None

                if account1.accounts:
                    balance1 = float(account1.accounts[0].available_balance)
                if account2.accounts:
                    balance2 = float(account2.accounts[0].available_balance)

                return balance1, balance2
        except Exception as exc:
            logger.warning("Failed to fetch account balances: %s", exc)

        return None, None

    def _record_trade_execution(
        self,
        market_index: int,
        base_amount_decimal: float,
        notional_usd: float,
    ) -> None:
        """Update aggregate trade metrics after a successful open."""
        self.total_volume_long += base_amount_decimal
        self.total_volume_short += base_amount_decimal
        self.total_notional += notional_usd

        market_stat = self.market_stats[market_index]
        market_stat['notional'] += notional_usd
        market_stat['volume_long'] += base_amount_decimal
        market_stat['volume_short'] += base_amount_decimal

    def _log_session_summary(self, prefix: str = "Session stats") -> None:
        """Emit a summary log line with cumulative session metrics."""
        logger.info(
            "%s -> total_notional=$%.2f | long_volume=%.6f | short_volume=%.6f | net_bleed=$%.2f",
            prefix,
            self.total_notional,
            self.total_volume_long,
            self.total_volume_short,
            self.realized_bleed,
        )

    async def _finalize_trade(self, position_info: dict) -> None:
        """Compute realized bleed for a trade once both legs are closed."""
        if position_info.get('finalized'):
            return

        pre_balances = position_info.get('pre_trade_balances')
        if not pre_balances or pre_balances[0] is None or pre_balances[1] is None:
            position_info['finalized'] = True
            return

        post_balances = await self._fetch_account_balances()
        if post_balances[0] is None or post_balances[1] is None:
            logger.warning(
                "Skipping bleed calculation for Trade #%s due to missing post-trade balances",
                position_info.get('trade_number', '?'),
            )
            position_info['finalized'] = True
            return

        delta_long = post_balances[0] - pre_balances[0]
        delta_short = post_balances[1] - pre_balances[1]
        trade_bleed = delta_long + delta_short

        self.realized_bleed += trade_bleed

        market_index = position_info.get('market_index')
        if market_index in self.market_stats:
            self.market_stats[market_index]['bleed'] += trade_bleed

        position_info['post_trade_balances'] = post_balances
        position_info['finalized'] = True

        logger.info(
            "Trade #%s realized PnL (bleed): $%.2f (long Δ=$%.2f, short Δ=$%.2f)",
            position_info.get('trade_number', '?'),
            trade_bleed,
            delta_long,
            delta_short,
        )
        self._log_session_summary("Session stats after close")

    async def _get_market_precision(self, market_id: int, fallback_price: float) -> int:
        """
        Get the official size_decimals precision for a market from Lighter API.
        
        Args:
            market_id: Market ID to fetch precision for
            fallback_price: Price to use for fallback precision guess
            
        Returns:
            Number of decimal places for base amount
        """
        cached_decimals = self.config.get_cached_size_decimals(market_id)
        if cached_decimals is not None:
            return cached_decimals

        try:
            logger.info("Refreshing size decimals for market %s from API", market_id)
            async with self.config.api_client() as api_client:
                order_api = lighter.OrderApi(api_client)
                order_book_details = await order_api.order_book_details(market_id=market_id)

            if order_book_details.order_book_details:
                for detail in order_book_details.order_book_details:
                    if detail.market_id == market_id:
                        self.config.cache_size_decimals(market_id, detail.size_decimals)
                        logger.info("Cached size decimals for market %s", market_id)
                        return detail.size_decimals

            # Fallback if not found
            logger.warning(f"Could not find size_decimals for market {market_id}, using fallback")
            return self._fallback_precision(fallback_price)

        except Exception as e:
            logger.warning(f"Error fetching market precision: {e}, using fallback")
            return self._fallback_precision(fallback_price)
    
    def _fallback_precision(self, price: float) -> int:
        """
        Fallback precision calculation based on asset price.
        Used only if API call fails.
        """
        if price >= 10000:
            return 5  # BTC-like assets
        elif price >= 1000:
            return 4  # ETH-like assets
        else:
            return 3  # Most other assets
        
    async def get_current_price(self, market_index: int) -> Optional[Tuple[float, float]]:
        """
        Fetch current best bid and ask prices from the order book.
        
        Args:
            market_index: Market ID to fetch prices for
            
        Returns:
            Tuple of (best_bid, best_ask) or (None, None) if unavailable
        """
        try:
            configuration = lighter.Configuration(self.config.base_url)
            api_client = lighter.ApiClient(configuration)
            order_api = lighter.OrderApi(api_client)
            
            order_book = await order_api.order_book_orders(market_id=market_index, limit=1)
            await api_client.close()
            
            if order_book.asks and order_book.bids:
                best_ask = float(order_book.asks[0].price)
                best_bid = float(order_book.bids[0].price)
                return best_bid, best_ask
            
            logger.warning(f"Order book for market {market_index} has no bids or asks")
            return None, None
                
        except Exception as e:
            logger.error(f"Error fetching price for market {market_index}: {e}")
            return None, None
    
    async def run_worker_command(self, account_config: dict, command_config: dict) -> dict:
        """
        Execute a command in an isolated worker process.
        
        Args:
            account_config: Account credentials and settings
            command_config: Command type and parameters
            
        Returns:
            Dictionary with 'success' status and result or error message
        """
        try:
            full_config = {'account': account_config, **command_config}
            
            # Launch isolated worker process
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                'account_worker.py',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send configuration and get result
            config_json = json.dumps(full_config)
            stdout, stderr = await process.communicate(input=config_json.encode())
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else 'Unknown error'
                return {'success': False, 'error': f'Worker failed: {error_msg}'}
            
            return json.loads(stdout.decode())
            
        except Exception as e:
            return {'success': False, 'error': f'Worker exception: {str(e)}'}
    
    async def update_leverage_both_accounts(
        self, 
        leverage: Optional[int] = None, 
        market_index: Optional[int] = None
    ):
        """
        Update leverage on both accounts with the same value.
        
        Args:
            leverage: Leverage to set (uses config.leverage if None)
            market_index: Market ID (uses config.market_index if None)
        """
        actual_leverage = leverage if leverage is not None else self.config.leverage
        actual_market = market_index if market_index is not None else self.config.market_index
        
        margin_mode = 'cross' if self.config.margin_mode == 0 else 'isolated'
        logger.info(f"Setting leverage: {actual_leverage}x ({margin_mode} margin)")
        
        account1_config = {
            'base_url': self.config.base_url,
            'private_key': self.config.account1_private_key,
            'account_index': self.config.account1_index,
            'api_key_index': self.config.account1_api_key_index,
        }
        
        account2_config = {
            'base_url': self.config.base_url,
            'private_key': self.config.account2_private_key,
            'account_index': self.config.account2_index,
            'api_key_index': self.config.account2_api_key_index,
        }
        
        leverage_command = {
            'command': 'update_leverage',
            'leverage': {
                'market_index': actual_market,
                'leverage': actual_leverage,
                'margin_mode': self.config.margin_mode
            }
        }
        
        # Update leverage for both accounts in parallel
        results = await asyncio.gather(
            self.run_worker_command(account1_config, leverage_command),
            self.run_worker_command(account2_config, leverage_command),
            return_exceptions=True
        )

        self._validate_worker_results(results, "update leverage on both accounts")

        logger.info("✅ Leverage updated on both accounts")
        return True
    
    async def update_leverage_for_accounts(
        self, 
        leverage_account1: int, 
        leverage_account2: int, 
        market_index: int
    ):
        """
        Update leverage independently for each account (asymmetric leverage).
        
        Args:
            leverage_account1: Leverage for account 1 (long)
            leverage_account2: Leverage for account 2 (short)
            market_index: Market ID
        """
        logger.info(f"Setting asymmetric leverage for market {market_index}:")
        logger.info(f"  Long: {leverage_account1}x | Short: {leverage_account2}x")
        
        account1_config = {
            'base_url': self.config.base_url,
            'private_key': self.config.account1_private_key,
            'account_index': self.config.account1_index,
            'api_key_index': self.config.account1_api_key_index,
        }
        
        account2_config = {
            'base_url': self.config.base_url,
            'private_key': self.config.account2_private_key,
            'account_index': self.config.account2_index,
            'api_key_index': self.config.account2_api_key_index,
        }
        
        leverage_command_account1 = {
            'command': 'update_leverage',
            'leverage': {
                'market_index': market_index,
                'leverage': leverage_account1,
                'margin_mode': self.config.margin_mode
            }
        }
        
        leverage_command_account2 = {
            'command': 'update_leverage',
            'leverage': {
                'market_index': market_index,
                'leverage': leverage_account2,
                'margin_mode': self.config.margin_mode
            }
        }
        
        # Update leverage for both accounts in parallel with different values
        results = await asyncio.gather(
            self.run_worker_command(account1_config, leverage_command_account1),
            self.run_worker_command(account2_config, leverage_command_account2),
            return_exceptions=True
        )

        self._validate_worker_results(results, "update leverage for accounts")

        logger.info("✅ Leverage updated on both accounts")
        return True
    
    async def execute_delta_neutral_trade(self) -> Tuple[bool, str]:
        """Execute simultaneous long and short market orders using isolated workers"""
        try:
            # Randomly select a market from the whitelist
            selected_market = self.select_random_market()
            
            # Get market info and determine leverage for this trade
            try:
                market_info = await self.config.get_market_info(selected_market)
                market_symbol = market_info['symbol']
                market_max_leverage = market_info['max_leverage']
                
                # Calculate leverage for this trade
                if self.config.use_dynamic_leverage:
                    # Select different leverage for each account
                    leverage_long = self.config.calculate_dynamic_leverage(market_max_leverage)
                    leverage_short = self.config.calculate_dynamic_leverage(market_max_leverage)
                    logger.info(f"📊 Selected market: {market_symbol} (ID: {selected_market})")
                    logger.info(f"   🎲 Dynamic leverage - Long: {leverage_long}x | Short: {leverage_short}x (max: {market_max_leverage}x)")
                else:
                    leverage_long = self.config.leverage
                    leverage_short = self.config.leverage
                    logger.info(f"📊 Selected market: {market_symbol} (ID: {selected_market})")
                    
            except Exception as e:
                logger.warning(f"Could not fetch market info: {e}")
                market_symbol = f"Market {selected_market}"
                leverage_long = self.config.leverage
                leverage_short = self.config.leverage
                logger.info(f"📊 Selected market: {market_symbol} (ID: {selected_market})")
            
            # Update leverage for each account independently (if dynamic mode)
            if self.config.use_dynamic_leverage:
                await self.update_leverage_for_accounts(
                    leverage_account1=leverage_long,
                    leverage_account2=leverage_short,
                    market_index=selected_market
                )
            
            # Get current bid and ask for the selected market
            best_bid, best_ask = await self.get_current_price(selected_market)
            if best_bid is None and best_ask is None:
                return False, f"Failed to get current price for {market_symbol}"

            if best_bid is None or best_bid <= 0:
                if best_ask is not None and best_ask > 0:
                    logger.warning(
                        "Best bid missing or invalid for %s; falling back to best ask %.6f",
                        market_symbol,
                        best_ask,
                    )
                    best_bid = best_ask
                else:
                    logger.warning(
                        "Unable to determine valid best bid for %s (value: %s)",
                        market_symbol,
                        best_bid,
                    )
                    return False, f"Failed to get valid best bid for {market_symbol}"

            if best_ask is None or best_ask <= 0:
                if best_bid is not None and best_bid > 0:
                    logger.warning(
                        "Best ask missing or invalid for %s; falling back to best bid %.6f",
                        market_symbol,
                        best_bid,
                    )
                    best_ask = best_bid
                else:
                    logger.warning(
                        "Unable to determine valid best ask for %s (value: %s)",
                        market_symbol,
                        best_ask,
                    )
                    return False, f"Failed to get valid best ask for {market_symbol}"

            max_slippage = self.config.max_slippage
            long_execution_price = best_ask * (1 + max_slippage)
            short_execution_price = best_bid * (1 - max_slippage)
            mid_price = (best_bid + best_ask) / 2

            if long_execution_price <= 0 or short_execution_price <= 0:
                logger.warning(
                    "Computed execution prices invalid for %s (long: %s, short: %s)",
                    market_symbol,
                    long_execution_price,
                    short_execution_price,
                )
                return False, f"Invalid execution prices for {market_symbol}"

            # --- PRE-TRADE SAFEGUARD: Check Bid-Ask Spread ---
            spread = best_ask - best_bid
            spread_percentage = (spread / best_ask) * 100
            max_spread_percentage = 0.1  # Allow up to 0.1% spread

            if spread_percentage > max_spread_percentage:
                logger.warning(f"Spread ({spread_percentage:.4f}%) exceeds max ({max_spread_percentage}%) - skipping trade")
                return False, f"Spread too wide for {market_symbol}"
            
            # Calculate base_amount from USDT margin target
            if self.config.base_amount_in_usdt:
                # Calculate effective leverage for this trade
                effective_leverage_long = (
                    leverage_long if self.config.use_dynamic_leverage
                    else self.config.leverage
                )
                effective_leverage_short = (
                    leverage_short if self.config.use_dynamic_leverage 
                    else self.config.leverage
                )
                avg_leverage = (effective_leverage_long + effective_leverage_short) / 2
                
                # Fetch official precision from Lighter API
                precision_decimals = await self._get_market_precision(selected_market, mid_price)
                precision_multiplier = 10 ** precision_decimals
                
                # Calculate base_amount from margin target
                # Formula: base_amount = (margin * leverage / price) * precision_multiplier
                target_notional = self.config.base_amount_in_usdt * avg_leverage
                asset_amount = target_notional / mid_price
                base_amount = max(1, round(asset_amount * precision_multiplier))

                # Calculate actual values for logging
                base_amount_decimal = base_amount / precision_multiplier
                actual_notional_usd = base_amount_decimal * mid_price
                margin_long = actual_notional_usd / effective_leverage_long
                margin_short = actual_notional_usd / effective_leverage_short
                
                logger.info(f"Using BASE_AMOUNT_IN_USDT: ${self.config.base_amount_in_usdt:.2f} (target margin)")
                logger.info(f"  Asset: {market_symbol.split('-')[0]}, Price: ${mid_price:.2f}")
                logger.info(f"  Precision: {precision_decimals} decimals (multiplier: {precision_multiplier})")
                logger.info(f"  Average leverage: {avg_leverage:.1f}x")
                logger.info(f"  Target notional: ${target_notional:.2f}")
                logger.info(f"  Asset amount: {base_amount_decimal:.{precision_decimals}f}")
                logger.info(f"  Actual notional: ${actual_notional_usd:.2f}")
                logger.info(f"  Long: ${actual_notional_usd:.2f} notional / {effective_leverage_long}x = ${margin_long:.2f} margin")
                logger.info(f"  Short: ${actual_notional_usd:.2f} notional / {effective_leverage_short}x = ${margin_short:.2f} margin")
                # Store precision for later display
                display_precision = precision_decimals
                display_multiplier = precision_multiplier
            else:
                base_amount = self.config.base_amount
                # Default to 4 decimals if not using USDT sizing
                display_precision = 4
                display_multiplier = 10000
                base_amount_decimal = base_amount / display_multiplier
                actual_notional_usd = base_amount_decimal * mid_price
            
            logger.info(f"Executing delta neutral trade on {market_symbol}:")
            logger.info(f"  Base amount: {base_amount / display_multiplier:.{display_precision}f} {market_symbol.split('-')[0]}")
            logger.info(f"  Best Bid: ${best_bid:.2f}, Best Ask: ${best_ask:.2f}")
            logger.info(f"  Spread: ${spread:.2f} ({spread_percentage:.3f}%)")
            logger.info(f"  Long leverage: {leverage_long}x | Short leverage: {leverage_short}x")
            
            # Snapshot balances before submitting orders
            pre_trade_balances = await self._fetch_account_balances()

            # Prepare account configurations
            account1_config = {
                'base_url': self.config.base_url,
                'private_key': self.config.account1_private_key,
                'account_index': self.config.account1_index,
                'api_key_index': self.config.account1_api_key_index,
            }
            
            account2_config = {
                'base_url': self.config.base_url,
                'private_key': self.config.account2_private_key,
                'account_index': self.config.account2_index,
                'api_key_index': self.config.account2_api_key_index,
            }
            
            # Prepare order commands
            timestamp_ms = int(datetime.now().timestamp() * 1000)
            
            # For a true market order, we set a very wide price boundary.
            # For a buy order, we set a very high price.
            # For a sell order, we set a very low price (e.g., 1).
            long_command = {
                'command': 'execute_true_market_order',
                'order': {
                    'market_index': selected_market,
                    'base_amount': base_amount,
                    'is_ask': False,  # Buy = Long
                    'client_order_index': timestamp_ms % 1000000,
                    'execution_price': long_execution_price
                }
            }

            short_command = {
                'command': 'execute_true_market_order',
                'order': {
                    'market_index': selected_market,
                    'base_amount': base_amount,
                    'is_ask': True,  # Sell = Short
                    'client_order_index': (timestamp_ms + 1) % 1000000,
                    'execution_price': short_execution_price
                }
            }

            logger.info(
                "  Execution limits -> Long buy ≤ $%.6f | Short sell ≥ $%.6f (max slippage %.2f%%)",
                long_execution_price,
                short_execution_price,
                max_slippage * 100,
            )
            
            # Execute both orders in parallel using isolated workers
            results = await asyncio.gather(
                self.run_worker_command(account1_config, long_command),
                self.run_worker_command(account2_config, short_command),
                return_exceptions=True
            )
            
            long_result, short_result = results
            
            # Check results
            long_success = isinstance(long_result, dict) and long_result.get('success', False)
            short_success = isinstance(short_result, dict) and short_result.get('success', False)
            
            if long_success:
                logger.info(f"✅ Long order (Account 1): TX {long_result.get('tx_hash', 'N/A')[:16]}...")
            else:
                logger.error(f"❌ Long order failed: {long_result.get('error', 'Unknown error') if isinstance(long_result, dict) else str(long_result)}")
            
            if short_success:
                logger.info(f"✅ Short order (Account 2): TX {short_result.get('tx_hash', 'N/A')[:16]}...")
            else:
                logger.error(f"❌ Short order failed: {short_result.get('error', 'Unknown error') if isinstance(short_result, dict) else str(short_result)}")
            
            # Both must succeed for delta neutral
            if long_success and short_success:
                # Update market stats
                self.market_stats[selected_market]['trades'] += 1
                self.market_stats[selected_market]['successful'] += 1
                self._record_trade_execution(
                    selected_market,
                    base_amount_decimal,
                    actual_notional_usd,
                )

                # Schedule position closing
                close_delay = random.randint(self.config.min_close_delay, self.config.max_close_delay)
                close_time = asyncio.get_event_loop().time() + close_delay
                position_info = {
                    'market_index': selected_market,
                    'market_symbol': market_symbol,
                    'base_amount': base_amount,
                    'base_amount_decimal': base_amount_decimal,
                    'notional': actual_notional_usd,
                    'close_time': close_time,
                    'next_retry_time': close_time,
                    'close_delay': close_delay,
                    'trade_number': self.trade_count,
                    'close_failures': 0,
                    'long_closed': False,
                    'short_closed': False,
                    'pre_trade_balances': pre_trade_balances,
                }
                self.open_positions.append(position_info)

                logger.info(f"✅ Delta neutral trade executed successfully on {market_symbol}")
                logger.info(f"📅 Position will close in {close_delay} seconds")
                self._log_session_summary("Session stats after open")
                return True, "Success"
            else:
                # Update market stats for failed trade
                self.market_stats[selected_market]['trades'] += 1
                self._log_session_summary("Session stats after failed trade")
                return False, f"One or both orders failed for {market_symbol}"

        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            self._log_session_summary("Session stats after exception")
            return False, str(e)
    
    async def close_positions_task(self):
        """Background task to close positions when their time comes"""
        while self.is_running:
            try:
                current_time = asyncio.get_event_loop().time()
                positions_to_close = []
                remaining_positions = []

                for pos in self.open_positions:
                    next_retry_time = pos.get('next_retry_time', pos.get('close_time', 0))
                    if next_retry_time is None:
                        next_retry_time = pos.get('close_time', 0)
                    if current_time >= next_retry_time:
                        positions_to_close.append(pos)
                    else:
                        remaining_positions.append(pos)

                # Close positions that are ready
                if positions_to_close:
                    retry_positions = []
                    for pos in positions_to_close:
                        market_symbol = pos.get('market_symbol', f'Market {pos["market_index"]}')
                        logger.info(f"\n{'='*60}")
                        logger.info(f"Closing positions from Trade #{pos['trade_number']} - {market_symbol}")
                        logger.info(f"{'='*60}")
                        close_result = await self.close_position_pair(
                            pos['market_index'],
                            pos['base_amount'],
                            market_symbol,
                            close_long=not pos.get('long_closed', False),
                            close_short=not pos.get('short_closed', False)
                        )

                        long_success = close_result.get('long_success', False)
                        short_success = close_result.get('short_success', False)

                        if long_success:
                            pos['long_closed'] = True
                        if short_success:
                            pos['short_closed'] = True

                        if pos.get('long_closed') and pos.get('short_closed'):
                            await self._finalize_trade(pos)
                            logger.info(
                                "✅ Successfully closed both legs for Trade #%s",
                                pos['trade_number']
                            )
                            pos['close_failures'] = 0
                            pos['next_retry_time'] = None
                        else:
                            failure_count = pos.get('close_failures', 0) + 1
                            pos['close_failures'] = failure_count
                            backoff_seconds = self.close_retry_backoff_seconds * max(1, failure_count)
                            pos['next_retry_time'] = asyncio.get_event_loop().time() + backoff_seconds
                            retry_positions.append(pos)

                            logger.warning(
                                "Retrying Trade #%s in %ss (attempt %s) due to close failure",
                                pos['trade_number'],
                                backoff_seconds,
                                failure_count,
                            )

                            if failure_count >= self.max_close_retries:
                                if not self.close_failure_alert_active:
                                    logger.error(
                                        "🚨 Trade #%s failed to close after %s attempts. Manual intervention required before"
                                        " continuing new trades.",
                                        pos['trade_number'],
                                        failure_count,
                                    )
                                self.close_failure_alert_active = True

                    # Only update the list after closing is complete
                    self.open_positions = remaining_positions + retry_positions

                    if self.close_failure_alert_active:
                        if not any(
                            p.get('close_failures', 0) >= self.max_close_retries
                            for p in self.open_positions
                        ):
                            self.close_failure_alert_active = False
                            logger.info("✅ Close failure alert cleared after successful retries.")

                await asyncio.sleep(1)  # Check every second

            except Exception as e:
                logger.error(f"Error in close positions task: {e}")
                await asyncio.sleep(5)
    
    async def close_position_pair(
        self,
        market_index: int,
        base_amount: int,
        market_symbol: str = None,
        close_long: bool = True,
        close_short: bool = True
    ) -> Dict[str, Any]:
        """Close both long and short positions for a specific market.

        Returns structured results for both legs so the caller can
        determine retry/escalation strategy.
        """
        long_close_result: Any = {'success': False}
        short_close_result: Any = {'success': False}

        try:
            if market_symbol is None:
                market_symbol = f"Market {market_index}"
            # Prepare account configurations
            account1_config = {
                'base_url': self.config.base_url,
                'private_key': self.config.account1_private_key,
                'account_index': self.config.account1_index,
                'api_key_index': self.config.account1_api_key_index,
            }

            account2_config = {
                'base_url': self.config.base_url,
                'private_key': self.config.account2_private_key,
                'account_index': self.config.account2_index,
                'api_key_index': self.config.account2_api_key_index,
            }

            best_bid, best_ask = await self.get_current_price(market_index)

            if close_long and (best_bid is None or best_bid <= 0):
                if best_ask is not None and best_ask > 0:
                    logger.warning(
                        "Best bid missing or invalid for %s while closing long; using ask %.6f",
                        market_symbol,
                        best_ask,
                    )
                    best_bid = best_ask
                else:
                    logger.warning(
                        "Unable to determine valid best bid for %s when closing long (value: %s)",
                        market_symbol,
                        best_bid,
                    )
                    return {
                        'long_success': False,
                        'short_success': False,
                        'long_result': {'success': False, 'error': 'Invalid best bid'},
                        'short_result': {'success': False, 'error': 'Invalid best bid'},
                    }

            if close_short and (best_ask is None or best_ask <= 0):
                if best_bid is not None and best_bid > 0:
                    logger.warning(
                        "Best ask missing or invalid for %s while closing short; using bid %.6f",
                        market_symbol,
                        best_bid,
                    )
                    best_ask = best_bid
                else:
                    logger.warning(
                        "Unable to determine valid best ask for %s when closing short (value: %s)",
                        market_symbol,
                        best_ask,
                    )
                    return {
                        'long_success': False,
                        'short_success': False,
                        'long_result': {'success': False, 'error': 'Invalid best ask'},
                        'short_result': {'success': False, 'error': 'Invalid best ask'},
                    }

            max_slippage = self.config.max_slippage
            close_long_execution_price = None
            close_short_execution_price = None

            if close_long:
                close_long_execution_price = best_bid * (1 - max_slippage)
                if close_long_execution_price <= 0:
                    logger.warning(
                        "Computed close price invalid for long leg on %s (price: %s)",
                        market_symbol,
                        close_long_execution_price,
                    )
                    return {
                        'long_success': False,
                        'short_success': False,
                        'long_result': {'success': False, 'error': 'Invalid long close price'},
                        'short_result': {'success': False, 'error': 'Invalid long close price'},
                    }

            if close_short:
                close_short_execution_price = best_ask * (1 + max_slippage)
                if close_short_execution_price <= 0:
                    logger.warning(
                        "Computed close price invalid for short leg on %s (price: %s)",
                        market_symbol,
                        close_short_execution_price,
                    )
                    return {
                        'long_success': False,
                        'short_success': False,
                        'long_result': {'success': False, 'error': 'Invalid short close price'},
                        'short_result': {'success': False, 'error': 'Invalid short close price'},
                    }

            if close_long or close_short:
                limit_messages = []
                if close_long:
                    limit_messages.append(
                        f"Long sell ≥ ${close_long_execution_price:.6f}"
                    )
                if close_short:
                    limit_messages.append(
                        f"Short buy ≤ ${close_short_execution_price:.6f}"
                    )
                logger.info(
                    "  Close limits -> %s (max slippage %.2f%%)",
                    " | ".join(limit_messages),
                    max_slippage * 100,
                )

            # Close commands
            close_long_command = {
                'command': 'execute_true_market_order',
                'order': {
                    'market_index': market_index,
                    'base_amount': base_amount,
                    'is_ask': True,  # Sell to close long
                    'client_order_index': int(datetime.now().timestamp() * 1000 + 2) % 1000000,
                    'reduce_only': True,
                    'execution_price': close_long_execution_price if close_long_execution_price is not None else 0
                }
            }

            close_short_command = {
                'command': 'execute_true_market_order',
                'order': {
                    'market_index': market_index,
                    'base_amount': base_amount,
                    'is_ask': False, # Buy to close short
                    'client_order_index': int(datetime.now().timestamp() * 1000 + 3) % 1000000,
                    'reduce_only': True,
                    'execution_price': close_short_execution_price if close_short_execution_price is not None else 0
                }
            }

            # Close positions sequentially to avoid SDK race conditions
            # (parallel closing sometimes triggers SDK bugs)
            if close_long:
                long_close_result = await self.run_worker_command(account1_config, close_long_command)
            else:
                long_close_result = {'success': True, 'skipped': True}

            if close_short and close_long:
                await asyncio.sleep(0.5)  # Small delay to avoid SDK issues when both legs run

            if close_short:
                short_close_result = await self.run_worker_command(account2_config, close_short_command)
            else:
                short_close_result = {'success': True, 'skipped': True}

            long_success = (
                isinstance(long_close_result, dict) and long_close_result.get('success')
            ) or (not close_long)
            short_success = (
                isinstance(short_close_result, dict) and short_close_result.get('success')
            ) or (not close_short)

            # Log results with better error reporting
            if close_long:
                if long_success:
                    tx_hash = long_close_result.get('tx_hash', 'N/A')
                    logger.info(f"✅ Closed long position (Account 1): TX {tx_hash[:16]}...")
                else:
                    error_msg = 'Unknown error'
                    if isinstance(long_close_result, dict):
                        error_msg = long_close_result.get('error') or long_close_result.get('message', 'Unknown')
                    elif isinstance(long_close_result, Exception):
                        error_msg = str(long_close_result)
                    logger.warning(f"⚠️  Long position close: {error_msg}")

            if close_short:
                if short_success:
                    tx_hash = short_close_result.get('tx_hash', 'N/A')
                    logger.info(f"✅ Closed short position (Account 2): TX {tx_hash[:16]}...")
                else:
                    error_msg = 'Unknown error'
                    if isinstance(short_close_result, dict):
                        error_msg = short_close_result.get('error') or short_close_result.get('message', 'Unknown')
                        if 'traceback' in short_close_result:
                            logger.error(f"Traceback:\n{short_close_result['traceback']}")
                    elif isinstance(short_close_result, Exception):
                        error_msg = str(short_close_result)
                    logger.warning(f"⚠️  Short position close: {error_msg}")

            return {
                'long_success': bool(long_success),
                'short_success': bool(short_success),
                'long_result': long_close_result,
                'short_result': short_close_result,
            }

        except Exception as e:
            logger.error(f"Error closing positions: {e}")
            return {
                'long_success': False,
                'short_success': False,
                'long_result': {'success': False, 'error': str(e)},
                'short_result': {'success': False, 'error': str(e)},
            }
    
    async def run_continuous(self):
        """Run continuous trading with configured interval"""
        self.is_running = True
        
        # Update leverage on both accounts first
        await self.update_leverage_both_accounts()
        
        # Start background task for closing positions
        close_task = asyncio.create_task(self.close_positions_task())
        
        logger.info(f"Starting continuous trading with {self.config.interval_seconds}s interval")
        logger.info(f"Positions will close randomly between {self.config.min_close_delay}-{self.config.max_close_delay}s after opening")
        
        try:
            while self.is_running:
                if self.close_failure_alert_active:
                    logger.error(
                        "⏸️  Close position retries exceeded threshold. Pausing new trades until manual intervention."
                    )
                    await asyncio.sleep(5)
                    continue

                self.trade_count += 1

                logger.info(f"\n{'='*60}")
                logger.info(f"Trade #{self.trade_count}")
                logger.info(f"{'='*60}")
                
                # Execute trade
                success, message = await self.execute_delta_neutral_trade()
                
                if success:
                    self.success_count += 1
                else:
                    logger.warning(f"✗ {message}")
                
                # Log statistics
                success_rate = (self.success_count / self.trade_count * 100) if self.trade_count > 0 else 0
                logger.info(f"Success rate: {self.success_count}/{self.trade_count} ({success_rate:.1f}%)")
                
                # Check if we've reached max trades
                if self.config.max_trades > 0 and self.trade_count >= self.config.max_trades:
                    logger.info(f"\nReached maximum trade limit ({self.config.max_trades})")
                    break
                
                # Wait before next trade with random delay
                open_delay = random.randint(self.config.min_open_delay, self.config.max_open_delay)
                logger.info(f"Waiting {open_delay}s until next trade (range: {self.config.min_open_delay}-{self.config.max_open_delay}s)...")
                await asyncio.sleep(open_delay)
                
        except KeyboardInterrupt:
            logger.info("\nReceived interrupt signal")
        finally:
            # Wait for any remaining open positions to be closed by the background task
            if self.open_positions:
                logger.info(f"\nWaiting for {len(self.open_positions)} remaining position(s) to close...")
                while self.open_positions:
                    await asyncio.sleep(1)
            
            # Now that all positions are closed, we can stop the background task
            self.is_running = False
            close_task.cancel()
            try:
                await close_task
            except asyncio.CancelledError:
                pass  # Expected on cancellation
            
            # Display market statistics
            if len(self.config.market_whitelist) > 1:
                logger.info("\n" + "="*60)
                logger.info("Market Statistics")
                logger.info("="*60)
                for market_id in sorted(self.market_stats.keys()):
                    stats = self.market_stats[market_id]
                    if stats['trades'] > 0:
                        success_rate = (stats['successful'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
                        logger.info(f"  Market {market_id}: {stats['successful']}/{stats['trades']} trades ({success_rate:.1f}% success)")
                        logger.info(
                            "    Totals -> notional=$%.2f | long_volume=%.6f | short_volume=%.6f | bleed=$%.2f",
                            stats['notional'],
                            stats['volume_long'],
                            stats['volume_short'],
                            stats['bleed'],
                        )

            self._log_session_summary("Final session stats")
            logger.info("Bot stopped")


async def main():
    """Main entry point"""
    logger.info("="*60)
    logger.info("Delta Neutral Volume Generation Bot for Lighter DEX")
    logger.info("="*60)
    
    # Load configuration
    try:
        config = BotConfig.from_env()
        config.validate()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Display configuration
    logger.info("\nConfiguration:")
    logger.info(f"  Base URL: {config.base_url}")
    if 'testnet' in config.base_url.lower():
        logger.info("  ✓ Testnet mode - Safe for testing")
    else:
        logger.warning("  ⚠️  MAINNET MODE - Using real funds!")
    logger.info(f"  Market Whitelist: {config.market_whitelist} ({len(config.market_whitelist)} market(s))")
    logger.info(f"  Account 1 Index: {config.account1_index}")
    logger.info(f"  Account 2 Index: {config.account2_index}")
    if config.base_amount_in_usdt:
        logger.info(f"  Trade Size: ${config.base_amount_in_usdt:.2f} USDT (converted to asset at market price)")
    else:
        logger.info(f"  Base Amount: {config.base_amount / 10000:.4f}")
    logger.info(f"  Max Slippage: {config.max_slippage * 100:.2f}%")
    if config.use_dynamic_leverage:
        logger.info(f"  Leverage: DYNAMIC (market_max - {config.leverage_buffer} to market_max) 🎲")
    else:
        logger.info(f"  Leverage: {config.leverage}x (Fixed)")
    logger.info(f"  Margin Mode: {'Cross' if config.margin_mode == 0 else 'Isolated'}")
    logger.info(f"  Open New Trade Delay: {config.min_open_delay}-{config.max_open_delay}s (randomized) 🎲")
    logger.info(f"  Position Close Delay: {config.min_close_delay}-{config.max_close_delay}s (randomized)")
    logger.info(f"  Max Trades: {config.max_trades if config.max_trades > 0 else 'Unlimited'}")
    logger.info(f"  Batch Mode: {config.use_batch_mode}")
    logger.info("")
    
    # Validate leverage against Lighter API limits
    logger.info("Validating configuration against Lighter API...")
    try:
        await config.validate_with_api()
        max_leverage = await config.get_market_max_leverage()
        logger.info(f"✅ Leverage validation passed")
        logger.info(f"   Market {config.market_index} max leverage: {max_leverage}x")
        logger.info(f"   Your configured leverage: {config.leverage}x")
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        logger.error("\nPlease check your configuration and try again.")
        sys.exit(1)
    
    logger.info("")
    
    # Create and run orchestrator
    orchestrator = DeltaNeutralOrchestrator(config)
    await orchestrator.run_continuous()
    
    logger.info("\nExiting...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot connections closed")
        print("\nExiting...")
        sys.exit(0)