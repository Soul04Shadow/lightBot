import asyncio
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from unittest.mock import AsyncMock

import pytest

from config import BotConfig
from delta_neutral_orchestrator import DeltaNeutralOrchestrator


def make_config() -> BotConfig:
    return BotConfig(
        base_url="https://example.test",
        account1_private_key="0xabc",
        account1_index=0,
        account1_api_key_index=0,
        account2_private_key="0xdef",
        account2_index=1,
        account2_api_key_index=0,
        market_index=1,
        market_whitelist=[1],
        base_amount=1000,
        base_amount_in_usdt=None,
        max_slippage=0.01,
        max_spread_percent=0.1,
        leverage=5,
        use_dynamic_leverage=False,
        leverage_buffer=0,
        margin_mode=0,
        interval_seconds=0,
        min_open_delay=0,
        max_open_delay=0,
        min_close_delay=0,
        max_close_delay=0,
        max_trades=0,
        use_batch_mode=False,
        market_metadata_ttl_seconds=300,
    )


def test_execute_trade_uses_slippage_limits():
    orchestrator = DeltaNeutralOrchestrator(make_config())
    orchestrator.select_random_market = lambda: 1
    orchestrator.config.get_market_info = AsyncMock(return_value={
        "symbol": "BTC-USDT",
        "max_leverage": 20,
        "price_decimals": 4,
    })
    orchestrator.get_current_price = AsyncMock(return_value=(100.0, 100.05))
    orchestrator.run_worker_command = AsyncMock(
        side_effect=[{"success": True}, {"success": True}]
    )
    orchestrator._get_balances = AsyncMock(return_value=((1000.0, 1000.0), True))

    success, _ = asyncio.run(orchestrator.execute_delta_neutral_trade())

    assert success is True
    long_command = orchestrator.run_worker_command.await_args_list[0].args[1]
    short_command = orchestrator.run_worker_command.await_args_list[1].args[1]

    expected_long_price = 100.05 * 1.01
    expected_short_price = 100.0 * 0.99
    expected_long_ticks = int(Decimal(str(expected_long_price)).scaleb(4).to_integral_value(rounding=ROUND_UP))
    expected_short_ticks = int(Decimal(str(expected_short_price)).scaleb(4).to_integral_value(rounding=ROUND_DOWN))

    assert long_command["order"]["execution_price"] == expected_long_ticks
    assert short_command["order"]["execution_price"] == expected_short_ticks


def test_execute_trade_falls_back_when_missing_bid():
    orchestrator = DeltaNeutralOrchestrator(make_config())
    orchestrator.select_random_market = lambda: 1
    orchestrator.config.get_market_info = AsyncMock(return_value={
        "symbol": "BTC-USDT",
        "max_leverage": 20,
        "price_decimals": 4,
    })
    orchestrator.get_current_price = AsyncMock(return_value=(None, 50.0))
    orchestrator.run_worker_command = AsyncMock(
        side_effect=[{"success": True}, {"success": True}]
    )
    orchestrator._get_balances = AsyncMock(return_value=((1000.0, 1000.0), True))

    success, _ = asyncio.run(orchestrator.execute_delta_neutral_trade())

    assert success is True
    short_command = orchestrator.run_worker_command.await_args_list[1].args[1]
    expected_short_price = 50.0 * 0.99
    expected_short_ticks = int(Decimal(str(expected_short_price)).scaleb(4).to_integral_value(rounding=ROUND_DOWN))
    assert short_command["order"]["execution_price"] == expected_short_ticks


def test_execute_trade_blocks_on_wide_spread():
    config = make_config()
    config.max_spread_percent = 0.05  # tighten guard to 0.05%
    orchestrator = DeltaNeutralOrchestrator(config)
    orchestrator.select_random_market = lambda: 1
    orchestrator.config.get_market_info = AsyncMock(return_value={
        "symbol": "BTC-USDT",
        "max_leverage": 20,
        "price_decimals": 4,
    })
    orchestrator.get_current_price = AsyncMock(return_value=(100.0, 100.2))
    orchestrator.run_worker_command = AsyncMock()
    orchestrator._get_balances = AsyncMock(return_value=((1000.0, 1000.0), True))

    success, message = asyncio.run(orchestrator.execute_delta_neutral_trade())

    assert success is False
    assert "Spread too wide" in message
    orchestrator.run_worker_command.assert_not_awaited()


def test_execute_trade_respects_custom_spread_threshold():
    config = make_config()
    config.max_spread_percent = 0.5  # allow up to 0.5%
    orchestrator = DeltaNeutralOrchestrator(config)
    orchestrator.select_random_market = lambda: 1
    orchestrator.config.get_market_info = AsyncMock(return_value={
        "symbol": "BTC-USDT",
        "max_leverage": 20,
        "price_decimals": 4,
    })
    orchestrator.get_current_price = AsyncMock(return_value=(100.0, 100.2))
    orchestrator.run_worker_command = AsyncMock(
        side_effect=[{"success": True}, {"success": True}]
    )
    orchestrator._get_balances = AsyncMock(return_value=((1000.0, 1000.0), True))

    success, _ = asyncio.run(orchestrator.execute_delta_neutral_trade())

    assert success is True
    assert orchestrator.run_worker_command.await_count == 2


def test_execute_trade_aborts_on_zero_prices():
    orchestrator = DeltaNeutralOrchestrator(make_config())
    orchestrator.select_random_market = lambda: 1
    orchestrator.config.get_market_info = AsyncMock(return_value={
        "symbol": "BTC-USDT",
        "max_leverage": 20,
        "price_decimals": 4,
    })
    orchestrator.get_current_price = AsyncMock(return_value=(0.0, 0.0))
    orchestrator.run_worker_command = AsyncMock()
    orchestrator._get_balances = AsyncMock(return_value=((1000.0, 1000.0), True))

    success, message = asyncio.run(orchestrator.execute_delta_neutral_trade())

    assert success is False
    assert "valid best bid" in message
    orchestrator.run_worker_command.assert_not_awaited()


def test_execute_trade_passes_integer_prices_to_worker():
    orchestrator = DeltaNeutralOrchestrator(make_config())
    orchestrator.select_random_market = lambda: 1
    orchestrator.config.get_market_info = AsyncMock(return_value={
        "symbol": "BTC-USDT",
        "max_leverage": 20,
        "price_decimals": 3,
    })
    orchestrator.get_current_price = AsyncMock(return_value=(100.0, 100.05))
    orchestrator.run_worker_command = AsyncMock(
        side_effect=[{"success": True}, {"success": True}]
    )
    orchestrator._get_balances = AsyncMock(return_value=((1000.0, 1000.0), True))

    success, _ = asyncio.run(orchestrator.execute_delta_neutral_trade())

    assert success is True
    for call in orchestrator.run_worker_command.await_args_list:
        command = call.args[1]
        execution_price = command["order"]["execution_price"]
        assert isinstance(execution_price, int)


def test_close_position_pair_uses_slippage_limits():
    orchestrator = DeltaNeutralOrchestrator(make_config())
    orchestrator.config.get_market_info = AsyncMock(return_value={
        "symbol": "BTC-USDT",
        "max_leverage": 20,
        "price_decimals": 4,
    })
    orchestrator.get_current_price = AsyncMock(return_value=(100.0, 102.0))
    orchestrator.run_worker_command = AsyncMock(return_value={"success": True})

    result = asyncio.run(
        orchestrator.close_position_pair(
            market_index=1,
            base_amount=1000,
            market_symbol="BTC-USDT",
            close_long=True,
            close_short=True,
        )
    )

    assert result["long_success"] is True
    assert result["short_success"] is True

    long_command = orchestrator.run_worker_command.await_args_list[0].args[1]
    short_command = orchestrator.run_worker_command.await_args_list[1].args[1]

    expected_long_price = 100.0 * 0.99
    expected_short_price = 102.0 * 1.01
    expected_long_ticks = int(Decimal(str(expected_long_price)).scaleb(4).to_integral_value(rounding=ROUND_DOWN))
    expected_short_ticks = int(Decimal(str(expected_short_price)).scaleb(4).to_integral_value(rounding=ROUND_UP))

    assert long_command["order"]["execution_price"] == expected_long_ticks
    assert short_command["order"]["execution_price"] == expected_short_ticks
