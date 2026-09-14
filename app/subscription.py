from aiogram import Bot
from aiogram.enums import ChatMemberStatus


def _normalize_chat_id(channel: str) -> int | str:
    value = channel.strip()
    if value.lstrip("-").isdigit():
        return int(value)
    return value


async def is_subscribed(bot: Bot, user_id: int, channel: str) -> bool:
    if not channel:
        return True
    try:
        member = await bot.get_chat_member(_normalize_chat_id(channel), user_id)
        return member.status in {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        }
    except Exception:
        return False
