import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from telegram_bot import TelegramBotController, TelegramNotifier


class DummyMessage:
    def __init__(self):
        self.sent_messages = []

    async def reply_text(self, text, **kwargs):  # pragma: no cover - exercised in tests
        self.sent_messages.append((text, kwargs))


class DummyUpdate(SimpleNamespace):
    def __init__(self, chat_id: int):
        super().__init__(
            effective_chat=SimpleNamespace(id=chat_id),
            message=DummyMessage(),
        )


class FakeOrchestrator:
    def get_status_snapshot(self):
        return {
            'is_running': True,
            'trade_count': 5,
            'success_count': 4,
            'open_positions': 1,
            'stop_reason': None,
        }

    async def get_balances_snapshot(self, *, force_refresh: bool = False):
        return ((120.5, 98.4), True)

    def get_config_view(self):
        return {
            'base_url': 'https://example.test',
            'market_index': 12,
            'market_whitelist': [12, 13],
            'leverage': 5,
            'use_dynamic_leverage': False,
        }

    def get_session_snapshot(self):
        return {
            'total_notional': 12345.67,
            'total_volume_long': 4.2,
            'total_volume_short': 4.2,
            'realized_bleed': -12.5,
            'market_stats': {
                12: {
                    'trades': 5,
                    'volume_long': 2.1,
                    'volume_short': 2.1,
                    'notional': 6000,
                    'bleed': -3.2,
                }
            },
        }


def test_trade_open_notification_reaches_operator():
    bot = AsyncMock()
    notifier = TelegramNotifier(bot=bot, operator_chat_ids=[111])

    asyncio.run(
        notifier.emit_trade_open(
            market='ETH-USD',
            trade_number=5,
            notional=1250.0,
            base_amount=0.52,
            close_delay=45,
        )
    )

    assert bot.send_message.await_count == 1
    _, kwargs = bot.send_message.await_args
    assert 'Trade #5 Opened' in kwargs['text']
    assert kwargs['parse_mode']


def test_status_command_renders_snapshot():
    bot = AsyncMock()
    notifier = TelegramNotifier(bot=bot, operator_chat_ids=[999])
    orchestrator = FakeOrchestrator()
    controller = TelegramBotController(orchestrator, notifier)

    update = DummyUpdate(chat_id=999)
    context = SimpleNamespace(args=[])

    asyncio.run(controller._handle_status(update, context))

    assert update.message.sent_messages
    text, kwargs = update.message.sent_messages[0]
    assert 'Trades: 5' in text
    assert kwargs['parse_mode']


def test_setlogchannel_updates_notifier():
    bot = AsyncMock()
    notifier = TelegramNotifier(bot=bot, operator_chat_ids=[123])
    orchestrator = FakeOrchestrator()
    controller = TelegramBotController(orchestrator, notifier)

    update = DummyUpdate(chat_id=123)
    context = SimpleNamespace(args=['-1001', 'on'])

    asyncio.run(controller._handle_setlogchannel(update, context))

    assert notifier.broadcast_chat_id == -1001
    assert notifier.auto_post_enabled is True
    assert update.message.sent_messages[-1][0].startswith('Log channel set')
