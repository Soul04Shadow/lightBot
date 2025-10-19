import asyncio
import pytest
from types import SimpleNamespace

from delta_neutral_orchestrator import DeltaNeutralOrchestrator


def make_config():
    return SimpleNamespace(
        market_whitelist=[1],
        account1_index=0,
        account2_index=1,
        api_client=None,
        min_account1_balance=None,
        min_account2_balance=None,
        min_combined_balance=None,
    )


def test_record_trade_execution_updates_aggregates():
    orchestrator = DeltaNeutralOrchestrator(make_config())

    orchestrator._record_trade_execution(1, base_amount_decimal=0.75, notional_usd=125.0)

    assert orchestrator.total_notional == pytest.approx(125.0)
    assert orchestrator.total_volume_long == pytest.approx(0.75)
    assert orchestrator.total_volume_short == pytest.approx(0.75)

    stats = orchestrator.market_stats[1]
    assert stats['notional'] == pytest.approx(125.0)
    assert stats['volume_long'] == pytest.approx(0.75)
    assert stats['volume_short'] == pytest.approx(0.75)


def test_finalize_trade_updates_realized_bleed(monkeypatch):
    orchestrator = DeltaNeutralOrchestrator(make_config())

    position_info = {
        'market_index': 1,
        'trade_number': 42,
        'pre_trade_balances': (1000.0, 2000.0),
    }

    async def mock_fetch_balances():
        return 995.5, 1998.0

    monkeypatch.setattr(orchestrator, '_fetch_account_balances', mock_fetch_balances)

    asyncio.run(orchestrator._finalize_trade(position_info))

    expected_bleed = (995.5 - 1000.0) + (1998.0 - 2000.0)
    assert orchestrator.realized_bleed == pytest.approx(expected_bleed)
    assert orchestrator.market_stats[1]['bleed'] == pytest.approx(expected_bleed)
    assert position_info['finalized'] is True

    # Ensure multiple calls do not double count
    asyncio.run(orchestrator._finalize_trade(position_info))
    assert orchestrator.realized_bleed == pytest.approx(expected_bleed)
    assert orchestrator.market_stats[1]['bleed'] == pytest.approx(expected_bleed)
