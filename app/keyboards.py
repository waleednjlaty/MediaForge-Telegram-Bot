from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def download_keyboard(job_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 فيديو 720p", callback_data=f"dl:video:{job_id}"),
            InlineKeyboardButton(text="🎵 MP3", callback_data=f"dl:audio:{job_id}"),
        ],
        [
            InlineKeyboardButton(text="ℹ️ معلومات", callback_data=f"dl:info:{job_id}"),
            InlineKeyboardButton(text="🖼 الصورة", callback_data=f"dl:thumb:{job_id}"),
        ],
    ])


def join_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 اشترك أولاً", url=url)],
        [InlineKeyboardButton(text="✅ تحقّق", callback_data="check_sub")],
    ])
