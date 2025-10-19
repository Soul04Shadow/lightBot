import asyncio
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock

sys.path.append(str(Path(__file__).resolve().parents[1]))

from account_worker import SingleAccountWorker


def test_update_leverage_skips_when_unchanged(caplog):
    worker = SingleAccountWorker({})
    worker.client = AsyncMock()
    worker.client.update_leverage = AsyncMock(return_value=None)

    caplog.set_level(logging.INFO, logger="account_worker")

    result, error = asyncio.run(worker.update_leverage(1, 5, 0))

    assert error is None
    assert result is True
    assert worker.client.update_leverage.await_count == 1

    caplog.clear()

    result, error = asyncio.run(worker.update_leverage(1, 5, 0))

    assert error is None
    assert result is True
    assert worker.client.update_leverage.await_count == 1
    assert "Skipping leverage update" in caplog.text


def test_update_leverage_refreshes_when_parameters_change(caplog):
    worker = SingleAccountWorker({})
    worker.client = AsyncMock()
    worker.client.update_leverage = AsyncMock(return_value=None)

    caplog.set_level(logging.INFO, logger="account_worker")

    asyncio.run(worker.update_leverage(1, 5, 0))

    caplog.clear()

    result, error = asyncio.run(worker.update_leverage(1, 6, 0))

    assert error is None
    assert result is True
    assert worker.client.update_leverage.await_count == 2
    assert "Updated leverage for market" in caplog.text


def test_update_leverage_refreshes_when_market_changes():
    worker = SingleAccountWorker({})
    worker.client = AsyncMock()
    worker.client.update_leverage = AsyncMock(return_value=None)

    asyncio.run(worker.update_leverage(1, 5, 0))
    asyncio.run(worker.update_leverage(2, 5, 0))

    assert worker.client.update_leverage.await_count == 2
