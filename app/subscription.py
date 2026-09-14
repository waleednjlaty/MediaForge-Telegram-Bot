from aiogram import Bot
from aiogram.enums import ChatMemberStatus


async def is_subscribed(bot: Bot, user_id: int, channel: str) -> bool:
    if not channel:
        return True
    try:
        member = await bot.get_chat_member(channel, user_id)
        return member.status in {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        }
    except Exception:
        return False
