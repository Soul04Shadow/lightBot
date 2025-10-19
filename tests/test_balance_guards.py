import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from delta_neutral_orchestrator import DeltaNeutralOrchestrator


def make_config(**overrides):
    base = dict(
        market_whitelist=[1],
        account1_index=0,
        account2_index=1,
        api_client=None,
        min_account1_balance=50.0,
        min_account2_balance=None,
        min_combined_balance=None,
        interval_seconds=60,
        min_open_delay=1,
        max_open_delay=1,
        min_close_delay=1,
        max_close_delay=1,
        max_trades=0,
        use_batch_mode=False,
        market_metadata_ttl_seconds=300,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_poll_and_enforce_balances_halts_when_floor_breached():
    orchestrator = DeltaNeutralOrchestrator(make_config())
    orchestrator.is_running = True
    orchestrator._get_balances = AsyncMock(return_value=((40.0, 120.0), True))

    result = asyncio.run(
        orchestrator._poll_and_enforce_balances(
            "unit-test",
            force_refresh=True,
        )
    )

    assert result is False
    assert orchestrator.is_running is False


def test_run_continuous_stops_when_floor_breached():
    orchestrator = DeltaNeutralOrchestrator(make_config())

    async def failing_poll(context: str, *, force_refresh: bool = False) -> bool:
        orchestrator.is_running = False
        return False

    orchestrator.update_leverage_both_accounts = AsyncMock()
    orchestrator.close_positions_task = AsyncMock()
    orchestrator.execute_delta_neutral_trade = AsyncMock()
    orchestrator._poll_and_enforce_balances = failing_poll

    asyncio.run(orchestrator.run_continuous())

    orchestrator.execute_delta_neutral_trade.assert_not_awaited()
    assert orchestrator.trade_count == 0
