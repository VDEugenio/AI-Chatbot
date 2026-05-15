"""
Telegram notifications for chatbot usage and page visits.

The notifier is fire-and-forget — every send is wrapped in a try/except so a
failed Telegram call NEVER affects the user-facing response. If either the
bot token or chat id is missing, all sends become no-ops silently, which
makes local development without Telegram credentials trivial.

Per-page-visit pings are throttled by (ip, path) to avoid spam from page
refreshes; per-chat pings are NOT throttled (every chat is a real signal).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict

import httpx

from .config import Settings
from .geoip import lookup as geoip_lookup

logger = logging.getLogger(__name__)


def _escape_html(s: str | None) -> str:
    """Telegram HTML mode allows only &, <, > as escapes."""
    if s is None:
        return ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# Short alias used in notification helpers.
_esc = _escape_html


def _truncate(s: str, n: int) -> str:
    s = s.strip()
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


class TelegramNotifier:
    """Async Telegram client wrapper. One instance per app process."""

    def __init__(self, settings: Settings) -> None:
        self._token = settings.telegram_bot_token
        self._chat_id = settings.telegram_chat_id
        self._enabled = bool(
            settings.enable_telegram_notifications
            and self._token
            and self._chat_id
        )
        self._throttle_seconds = settings.visit_throttle_seconds
        # (ip, path) → last-sent unix timestamp
        self._visit_seen: OrderedDict[tuple[str, str], float] = OrderedDict()
        # Only create the http client if we'll actually use it.
        self._client: httpx.AsyncClient | None = (
            httpx.AsyncClient(timeout=5.0) if self._enabled else None
        )
        if self._enabled:
            logger.info("Telegram notifier enabled")
        else:
            logger.info(
                "Telegram notifier disabled (missing token/chat_id or master switch off)"
            )

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def _send(self, text: str) -> None:
        if not self._enabled or self._client is None:
            return
        try:
            resp = await self._client.post(
                f"https://api.telegram.org/bot{self._token}/sendMessage",
                json={
                    "chat_id": self._chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
            data = resp.json()
            if not data.get("ok"):
                logger.warning(
                    "Telegram rejected message: %s", data.get("description", data)
                )
        except Exception as exc:
            # Notifications are best-effort. Log and move on.
            logger.warning("Telegram send failed: %s", exc)

    # ---------- public notification methods ----------

    async def notify_chat(
        self,
        question: str,
        answer_preview: str,
        ip: str,
        retriever: str,
        sources_count: int,
        elapsed_s: float,
        user_agent: str | None = None,
        visitor_context=None,
    ) -> None:
        """One ping per chatbot use. No throttling — every chat is signal."""
        if not self._enabled:
            return
        # Geo lookup is sync httpx; run off the event loop so we don't block.
        geo = await asyncio.to_thread(geoip_lookup, ip)

        visitor_line = ""
        if visitor_context is not None:
            name = getattr(visitor_context, "name", None)
            company = getattr(visitor_context, "company", None)
            if name or company:
                parts = []
                if name:
                    parts.append(_esc(name))
                if company:
                    parts.append(_esc(company))
                visitor_line = f"\n👤 {' @ '.join(parts)}"

        text = (
            f"🗨️ <b>New chat on vaughneugenio.com</b>{visitor_line}\n\n"
            f"<b>Q:</b> {_escape_html(_truncate(question, 300))}\n"
            f"<b>A:</b> {_escape_html(_truncate(answer_preview, 220))}\n\n"
            f"📍 {_escape_html(geo.label)}\n"
            f"🌐 IP: <code>{_escape_html(ip)}</code>\n"
            f"⚙️ {_escape_html(retriever)} · "
            f"{sources_count} sources · {elapsed_s:.1f}s"
        )
        if user_agent:
            text += f"\n🧭 {_escape_html(_truncate(user_agent, 120))}"
        await self._send(text)

    async def notify_visit(
        self,
        ip: str,
        path: str,
        referrer: str | None,
        user_agent: str | None = None,
    ) -> None:
        """One ping per page visit, throttled per (ip, path)."""
        if not self._enabled:
            return

        now = time.time()
        if self._throttle_seconds > 0:
            key = (ip, path)
            last = self._visit_seen.get(key)
            if last is not None and now - last < self._throttle_seconds:
                return
            self._visit_seen[key] = now
            # Trim cache occasionally so it can't grow unbounded.
            if len(self._visit_seen) > 2048:
                for k in list(self._visit_seen.keys())[:1024]:
                    self._visit_seen.pop(k, None)

        geo = await asyncio.to_thread(geoip_lookup, ip)
        ref_display = _escape_html(_truncate(referrer, 200)) if referrer else "direct"

        text = (
            "👀 <b>New visit</b> to vaughneugenio.com\n\n"
            f"<b>Path:</b> {_escape_html(path)}\n"
            f"📍 {_escape_html(geo.label)}\n"
            f"🌐 IP: <code>{_escape_html(ip)}</code>\n"
            f"↩️ Referrer: {ref_display}"
        )
        if user_agent:
            text += f"\n🧭 {_escape_html(_truncate(user_agent, 120))}"
        await self._send(text)

    async def notify_intake(
        self,
        ip: str,
        geo,
        visitor_context,  # VisitorContext
        user_agent: str | None = None,
    ) -> None:
        """Ping when a visitor submits the intake form."""
        if not self._enabled:
            return
        name = getattr(visitor_context, "name", None) or "—"
        company = getattr(visitor_context, "company", None) or "—"
        role = getattr(visitor_context, "role", None) or "—"
        ua_line = f"\n🧭 <code>{_esc(user_agent[:120])}</code>" if user_agent else ""
        text = (
            f"🧑 <b>Intake submitted — vaughneugenio.com</b>\n\n"
            f"👤 Name: {_esc(name)}\n"
            f"🏢 Company: {_esc(company)}\n"
            f"💼 Role: {_esc(role)}\n"
            f"📍 {_esc(geo.label)}\n"
            f"🌐 IP: <code>{_esc(ip)}</code>"
            f"{ua_line}"
        )
        await self._send(text)
