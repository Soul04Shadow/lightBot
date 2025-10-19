import asyncio
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
        market_whitelist=[1, 2],
        base_amount=1,
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


def test_update_leverage_both_accounts_success():
    orchestrator = DeltaNeutralOrchestrator(make_config())
    orchestrator.run_worker_command = AsyncMock(return_value={"success": True})

    result = asyncio.run(
        orchestrator.update_leverage_both_accounts(leverage=3, market_index=2)
    )

    assert result is True
    assert orchestrator.run_worker_command.await_count == 2


def test_update_leverage_both_accounts_failure_response_blocks_trading():
    orchestrator = DeltaNeutralOrchestrator(make_config())
    orchestrator.run_worker_command = AsyncMock(
        side_effect=[
            {"success": False, "error": "could not update leverage"},
            {"success": True},
        ]
    )

    with pytest.raises(RuntimeError, match="update leverage on both accounts") as exc_info:
        asyncio.run(
            orchestrator.update_leverage_both_accounts(leverage=3, market_index=2)
        )

    assert "could not update leverage" in str(exc_info.value)
    assert orchestrator.run_worker_command.await_count == 2


def test_update_leverage_both_accounts_exception_blocks_trading():
    orchestrator = DeltaNeutralOrchestrator(make_config())
    orchestrator.run_worker_command = AsyncMock(
        side_effect=[RuntimeError("boom"), {"success": True}]
    )

    with pytest.raises(RuntimeError, match="update leverage on both accounts") as exc_info:
        asyncio.run(
            orchestrator.update_leverage_both_accounts(leverage=3, market_index=2)
        )

    assert "boom" in str(exc_info.value)
    assert orchestrator.run_worker_command.await_count == 2


def test_update_leverage_for_accounts_failure_response_blocks_trading():
    orchestrator = DeltaNeutralOrchestrator(make_config())
    orchestrator.run_worker_command = AsyncMock(
        side_effect=[{"success": True}, {"success": False, "error": "bad leverage"}]
    )

    with pytest.raises(RuntimeError, match="update leverage for accounts") as exc_info:
        asyncio.run(orchestrator.update_leverage_for_accounts(3, 4, 2))

    assert "bad leverage" in str(exc_info.value)
    assert orchestrator.run_worker_command.await_count == 2
