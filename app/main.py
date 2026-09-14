import asyncio
import logging
from .config import Settings
from .bot import build_bot


async def main():
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    bot, dp = await build_bot(settings)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
