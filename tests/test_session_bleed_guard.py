import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from delta_neutral_orchestrator import DeltaNeutralOrchestrator


def make_config():
    return SimpleNamespace(
        market_whitelist=[101],
        account1_index=0,
        account2_index=1,
        api_client=None,
        min_account1_balance=None,
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
        max_session_bleed=-5.0,
    )


def test_finalize_trade_trips_session_bleed_guard(monkeypatch):
    orchestrator = DeltaNeutralOrchestrator(make_config())
    orchestrator.is_running = True

    position_info = {
        'market_index': 101,
        'trade_number': 1,
        'pre_trade_balances': (100.0, 100.0),
    }

    async def mock_fetch_balances():
        return 94.0, 94.0

    monkeypatch.setattr(orchestrator, '_fetch_account_balances', mock_fetch_balances)

    asyncio.run(orchestrator._finalize_trade(position_info))

    assert orchestrator.is_running is False
    assert orchestrator.stop_reason is not None
    assert 'Session bleed' in orchestrator.stop_reason


def test_run_continuous_stops_when_bleed_limit_hit():
    orchestrator = DeltaNeutralOrchestrator(make_config())

    orchestrator.update_leverage_both_accounts = AsyncMock()

    async def passing_poll(context: str, *, force_refresh: bool = False) -> bool:
        orchestrator._cached_balances = (100.0, 100.0)
        return True

    orchestrator._poll_and_enforce_balances = passing_poll

    orchestrator._fetch_account_balances = AsyncMock(return_value=(94.0, 94.0))

    async def close_task_stub():
        try:
            while True:
                if orchestrator.open_positions:
                    position = orchestrator.open_positions.pop(0)
                    await orchestrator._finalize_trade(position)
                    break
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            pass

    orchestrator.close_positions_task = close_task_stub

    async def execute_side_effect(*, pre_trade_balances):
        orchestrator.open_positions.append(
            {
                'market_index': 101,
                'trade_number': orchestrator.trade_count,
                'pre_trade_balances': pre_trade_balances,
            }
        )
        return True, 'ok'

    execute_mock = AsyncMock(side_effect=execute_side_effect)
    orchestrator.execute_delta_neutral_trade = execute_mock

    asyncio.run(orchestrator.run_continuous())

    assert execute_mock.await_count == 1
    assert orchestrator.is_running is False
    assert orchestrator.stop_reason is not None
    assert 'Session bleed' in orchestrator.stop_reason
