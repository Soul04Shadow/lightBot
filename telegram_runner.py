"""Entry point for running the Telegram bot alongside the orchestrator."""

from __future__ import annotations

import argparse
import logging
import sys

from telegram.ext import ApplicationBuilder

from config import BotConfig
from delta_neutral_orchestrator import DeltaNeutralOrchestrator
from telegram_bot import TelegramBotController, TelegramNotifier


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Telegram notifier service.")
    parser.add_argument(
        '--auto-post',
        dest='auto_post',
        action='store_true',
        help='Enable auto-posting trade logs to the broadcast channel (if configured).',
    )
    parser.add_argument(
        '--no-auto-post',
        dest='auto_post',
        action='store_false',
        help='Disable auto-posting trade logs.',
    )
    parser.set_defaults(auto_post=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)

    args = build_argument_parser().parse_args(argv)

    config = BotConfig.from_env()

    if not config.telegram_bot_token:
        raise RuntimeError(
            'TELEGRAM_BOT_TOKEN must be set to run the Telegram notifier service.'
        )

    if not config.telegram_operator_chat_ids:
        raise RuntimeError(
            'TELEGRAM_OPERATOR_CHAT_ID must be provided for Telegram notifier access control.'
        )

    application = ApplicationBuilder().token(config.telegram_bot_token).build()

    orchestrator = DeltaNeutralOrchestrator(config)

    auto_post_enabled = args.auto_post
    if auto_post_enabled is None:
        auto_post_enabled = config.telegram_broadcast_chat_id is not None

    notifier = TelegramNotifier(
        bot=application.bot,
        operator_chat_ids=config.telegram_operator_chat_ids,
        broadcast_chat_id=config.telegram_broadcast_chat_id,
        auto_post_enabled=auto_post_enabled,
    )

    orchestrator.attach_notifier(notifier)

    controller = TelegramBotController(orchestrator, notifier)
    controller.register(application)

    logging.info(
        "Starting Telegram bot for operators %s (broadcast=%s, auto_post=%s)",
        config.telegram_operator_chat_ids,
        config.telegram_broadcast_chat_id,
        notifier.auto_post_enabled,
    )

    application.run_polling()
    return 0


if __name__ == '__main__':
    sys.exit(main())

