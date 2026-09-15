import logging
from urllib.parse import urlparse

from aiogram import Bot
from aiogram.enums import ChatMemberStatus

logger = logging.getLogger(__name__)


def _normalize_chat_id(channel: str) -> int | str:
    value = (channel or "").strip()
    if not value:
        return ""
    if value.lstrip("-").isdigit():
        return int(value)
    return value


def _public_username(join_url: str) -> str | None:
    if not join_url:
        return None
    try:
        parsed = urlparse(join_url)
        if parsed.netloc.lower() not in {"t.me", "telegram.me", "www.t.me", "www.telegram.me"}:
            return None
        username = parsed.path.strip("/").split("/", 1)[0]
        if not username or username.startswith("+") or username.startswith("joinchat"):
            return None
        return f"@{username}"
    except Exception:
        return None


async def is_subscribed(bot: Bot, user_id: int, channel: str, join_url: str = "") -> bool:
    if not channel:
        return True

    candidates: list[int | str] = []
    primary = _normalize_chat_id(channel)
    if primary:
        candidates.append(primary)

    username = _public_username(join_url)
    if username and username not in candidates:
        candidates.append(username)

    last_error: Exception | None = None
    for chat_id in candidates:
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status in {
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.CREATOR,
            }:
                return True
            if member.status == ChatMemberStatus.RESTRICTED and getattr(member, "is_member", False):
                return True
            return False
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Forced-subscription check failed for chat=%r user=%s: %s",
                chat_id,
                user_id,
                exc,
            )

    if last_error:
        logger.error(
            "Unable to verify forced subscription. Make sure the bot is an administrator in the channel."
        )
    return False
