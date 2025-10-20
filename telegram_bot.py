"""Telegram bot helpers for interacting with the delta neutral orchestrator."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Sequence

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


class AuthorizationError(Exception):
    """Raised when a chat attempts to invoke a privileged command."""


@dataclass
class TelegramNotifier:
    """Simple wrapper around a Telegram bot instance for formatted messaging."""

    bot: Any
    operator_chat_ids: Iterable[int]
    broadcast_chat_id: Optional[int] = None
    auto_post_enabled: bool = False
    default_parse_mode: Optional[str] = ParseMode.MARKDOWN
    disable_link_previews: bool = True
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        self.operator_chat_ids = {int(chat_id) for chat_id in self.operator_chat_ids}
        if self.broadcast_chat_id is not None:
            self.broadcast_chat_id = int(self.broadcast_chat_id)

    async def send_operator_message(self, message: str, **kwargs: Any) -> None:
        """Send a message to every configured operator chat."""

        if not self.operator_chat_ids:
            logger.debug("No operator chat IDs configured; skipping operator broadcast")
            return

        params = {
            'parse_mode': self.default_parse_mode,
            'disable_web_page_preview': self.disable_link_previews,
        }
        params.update(kwargs)

        async with self._lock:
            for chat_id in self.operator_chat_ids:
                try:
                    await self.bot.send_message(chat_id=chat_id, text=message, **params)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning("Failed to send message to operator %s: %s", chat_id, exc)

    async def send_direct_message(self, chat_id: int, message: str, **kwargs: Any) -> None:
        """Send a message to an explicit chat ID."""

        params = {
            'parse_mode': self.default_parse_mode,
            'disable_web_page_preview': self.disable_link_previews,
        }
        params.update(kwargs)

        try:
            await self.bot.send_message(chat_id=chat_id, text=message, **params)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to deliver direct Telegram message to %s: %s", chat_id, exc)

    async def send_trade_log(self, message: str) -> None:
        """Send trade log style messages to the broadcast channel or operators."""

        target_chat = self.broadcast_chat_id if self.auto_post_enabled else None

        if target_chat is not None:
            await self.send_direct_message(target_chat, message)
        else:
            await self.send_operator_message(message)

    async def emit_trade_open(self, *, market: str, trade_number: int, notional: float,
                              base_amount: float, close_delay: int) -> None:
        """Broadcast a trade open summary."""

        message = (
            f"⚡️ *Trade #{trade_number} Opened*\n"
            f"• Market: `{market}`\n"
            f"• Base: {base_amount:.6f}\n"
            f"• Notional: ${notional:.2f}\n"
            f"• Close ETA: ~{close_delay}s"
        )
        await self.send_trade_log(message)

    async def emit_trade_close(self, *, market: str, trade_number: int, bleed: float,
                               delta_long: float, delta_short: float) -> None:
        """Broadcast a trade close summary with realized bleed."""

        emoji = "✅" if bleed >= 0 else "⚠️"
        message = (
            f"{emoji} *Trade #{trade_number} Closed*\n"
            f"• Market: `{market}`\n"
            f"• Bleed: ${bleed:.2f}\n"
            f"• ΔLong: ${delta_long:.2f}\n"
            f"• ΔShort: ${delta_short:.2f}"
        )
        await self.send_trade_log(message)

    async def emit_balance_snapshot(self, *, context: str, balances: Sequence[Optional[float]]) -> None:
        """Send a balance snapshot to operators for visibility."""

        account1, account2 = balances
        message = (
            f"📊 *Balance Snapshot* ({context})\n"
            f"• Account 1: {self._format_currency(account1)}\n"
            f"• Account 2: {self._format_currency(account2)}"
        )
        await self.send_operator_message(message)

    async def emit_drawdown_alert(self, *, context: str, reason: str) -> None:
        """Send a drawdown alert to operators."""

        message = (
            f"🚨 *Drawdown Alert*\n"
            f"• Context: {context}\n"
            f"• Reason: {reason}"
        )
        await self.send_operator_message(message)

    def _format_currency(self, value: Optional[float]) -> str:
        return f"${value:.2f}" if value is not None else "N/A"

    def set_broadcast_chat(self, chat_id: Optional[int], *, enable_auto_post: Optional[bool] = None) -> None:
        """Update the broadcast chat and optionally toggle auto-posting."""

        if chat_id is None:
            self.broadcast_chat_id = None
        else:
            self.broadcast_chat_id = int(chat_id)

        if enable_auto_post is not None:
            self.auto_post_enabled = bool(enable_auto_post)
        elif chat_id is None:
            self.auto_post_enabled = False


class TelegramBotController:
    """Register Telegram command handlers for the orchestrator."""

    def __init__(self, orchestrator: 'DeltaNeutralOrchestrator', notifier: TelegramNotifier):
        self.orchestrator = orchestrator
        self.notifier = notifier

    def register(self, application: Application) -> None:
        """Register command handlers on the supplied application."""

        application.add_handler(CommandHandler('status', self._handle_status))
        application.add_handler(CommandHandler('balances', self._handle_balances))
        application.add_handler(CommandHandler('config', self._handle_config))
        application.add_handler(CommandHandler('session', self._handle_session))
        application.add_handler(CommandHandler('setlogchannel', self._handle_setlogchannel))

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_authorized(update):
            return
        snapshot = self.orchestrator.get_status_snapshot()
        message = (
            "🛰 *Bot Status*\n"
            f"• Running: {'✅' if snapshot['is_running'] else '⏸'}\n"
            f"• Trades: {snapshot['trade_count']}\n"
            f"• Successes: {snapshot['success_count']}\n"
            f"• Open Positions: {snapshot['open_positions']}\n"
            f"• Stop Reason: {snapshot['stop_reason'] or '—'}"
        )
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )

    async def _handle_balances(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_authorized(update):
            return
        balances, refreshed = await self.orchestrator.get_balances_snapshot(force_refresh=True)
        message = (
            f"💰 *Account Balances* ({'fresh' if refreshed else 'cached'})\n"
            f"• Account 1: {self.notifier._format_currency(balances[0])}\n"
            f"• Account 2: {self.notifier._format_currency(balances[1])}"
        )
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )

    async def _handle_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_authorized(update):
            return
        config_info = self.orchestrator.get_config_view()
        message = (
            "⚙️ *Bot Configuration*\n"
            f"• Base URL: `{config_info['base_url']}`\n"
            f"• Market Index: {config_info['market_index']}\n"
            f"• Whitelist: {', '.join(map(str, config_info['market_whitelist']))}\n"
            f"• Leverage: {config_info['leverage']}x\n"
            f"• Dynamic Leverage: {'✅' if config_info['use_dynamic_leverage'] else '❌'}"
        )
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )

    async def _handle_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_authorized(update):
            return
        session = self.orchestrator.get_session_snapshot()
        market_lines = []
        for market_id, stats in session['market_stats'].items():
            market_lines.append(
                f"• Market {market_id}: trades={stats['trades']}, volume={stats['volume_long']:.6f}/"
                f"{stats['volume_short']:.6f}, bleed=${stats['bleed']:.2f}"
            )

        market_section = '\n'.join(market_lines) if market_lines else '• (no markets tracked)'

        message = (
            "📈 *Session Metrics*\n"
            f"• Total Notional: ${session['total_notional']:.2f}\n"
            f"• Long Volume: {session['total_volume_long']:.6f}\n"
            f"• Short Volume: {session['total_volume_short']:.6f}\n"
            f"• Realized Bleed: ${session['realized_bleed']:.2f}\n"
            f"• Markets:\n{market_section}"
        )
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )

    async def _handle_setlogchannel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_authorized(update):
            return

        args = context.args or []
        if not args:
            status = (
                f"Current log channel: {self.notifier.broadcast_chat_id or 'not set'}\n"
                f"Auto-posting: {'enabled' if self.notifier.auto_post_enabled else 'disabled'}"
            )
            await update.message.reply_text(status)
            return

        chat_arg = args[0]
        enable_arg = args[1] if len(args) > 1 else None

        if chat_arg.lower() in {'none', 'off'}:
            self.notifier.set_broadcast_chat(None, enable_auto_post=False)
            await update.message.reply_text("Log channel cleared; auto-posting disabled.")
            return

        try:
            new_chat_id = int(chat_arg)
        except ValueError:
            await update.message.reply_text("Chat ID must be a numeric value or 'off'.")
            return

        enable_auto = None
        if enable_arg:
            enable_auto = enable_arg.lower() in {'on', 'enable', 'true'}

        self.notifier.set_broadcast_chat(new_chat_id, enable_auto_post=enable_auto)

        await update.message.reply_text(
            f"Log channel set to {new_chat_id}. Auto-posting is "
            f"{'enabled' if self.notifier.auto_post_enabled else 'disabled'}."
        )

    async def _ensure_authorized(self, update: Update) -> bool:
        chat_id = update.effective_chat.id if update.effective_chat else None
        if chat_id is None or chat_id not in self.notifier.operator_chat_ids:
            if update.message:
                await update.message.reply_text("Unauthorized chat.")
            return False
        return True


__all__ = ['TelegramNotifier', 'TelegramBotController', 'AuthorizationError']

