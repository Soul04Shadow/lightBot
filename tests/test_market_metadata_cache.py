import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import lighter

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
        base_amount=1,
        base_amount_in_usdt=100.0,
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
        market_metadata_ttl_seconds=10,
    )


def test_execute_trade_reuses_cached_metadata(monkeypatch):
    config = make_config()
    orchestrator = DeltaNeutralOrchestrator(config)

    orchestrator.select_random_market = lambda: 1
    orchestrator.get_current_price = AsyncMock(return_value=(100.0, 100.05))
    orchestrator.run_worker_command = AsyncMock(return_value={"success": True})

    call_counts = {"order_book_details": 0}

    class DummyOrderApi:
        def __init__(self, api_client):
            self.api_client = api_client

        async def order_book_details(self, market_id):
            call_counts["order_book_details"] += 1
            detail = SimpleNamespace(
                market_id=market_id,
                symbol="BTC-USDT",
                min_initial_margin_fraction=500,
                size_decimals=4,
            )
            return SimpleNamespace(order_book_details=[detail])

    class DummyApiClient:
        async def close(self):
            pass

    monkeypatch.setattr(lighter, "Configuration", lambda base_url: base_url)
    monkeypatch.setattr(lighter, "ApiClient", lambda configuration: DummyApiClient())
    monkeypatch.setattr(lighter, "OrderApi", DummyOrderApi)

    fake_time = {"value": 1_000.0}
    monkeypatch.setattr(config, "_current_time", lambda: fake_time["value"])

    result = asyncio.run(orchestrator.execute_delta_neutral_trade())
    assert result == (True, "Success")
    assert call_counts["order_book_details"] == 2

    # Second trade within TTL should hit the cache
    result = asyncio.run(orchestrator.execute_delta_neutral_trade())
    assert result == (True, "Success")
    assert call_counts["order_book_details"] == 2

    # Advance time beyond TTL to force refresh
    fake_time["value"] += config.market_metadata_ttl_seconds + 1
    result = asyncio.run(orchestrator.execute_delta_neutral_trade())
    assert result == (True, "Success")
    assert call_counts["order_book_details"] == 4
