import asyncio
import logging
from html import escape
from pathlib import Path

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message, BufferedInputFile

from .config import Settings
from .db import Database
from .downloader import MediaDownloader
from .keyboards import download_keyboard, join_keyboard
from .limiter import RateLimiter
from .subscription import is_subscribed
from .utils import cache_key, extract_url, human_size, is_safe_supported_url
from .referral import parse_ref

router = Router()
logger = logging.getLogger(__name__)


class App:
    def __init__(self, settings: Settings):
        self.s = settings
        self.db = Database(settings.database_path)
        self.downloader = MediaDownloader(settings.max_file_mb, settings.download_concurrency)
        self.limiter = RateLimiter(settings.rate_limit_count, settings.rate_limit_window_seconds)
        self.bot: Bot | None = None
        self.username = ""

    async def require_access(self, user_id: int, message_or_cb) -> bool:
        if not self.s.force_sub_channel:
            return True
        ok = await is_subscribed(self.bot, user_id, self.s.force_sub_channel)
        if ok:
            return True
        text = "🔒 لاستخدام البوت اشترك بالقناة ثم اضغط «تحقّق»."
        kb = join_keyboard(self.s.force_sub_join_url or f"https://t.me/{self.s.force_sub_channel.lstrip('@')}")
        if isinstance(message_or_cb, Message):
            await message_or_cb.answer(text, reply_markup=kb)
        else:
            await message_or_cb.message.answer(text, reply_markup=kb)
        return False

app: App | None = None


@router.message(CommandStart())
async def start(m: Message):
    referred_by = parse_ref(m.text)
    await app.db.upsert_user(m.from_user, referred_by)
    if not await app.require_access(m.from_user.id, m):
        return
    await m.answer(
        "<b>⚡ MediaForge</b>\n\n"
        "نزّل محتوى عام من أشهر منصات السوشال ميديا مباشرة من تيليجرام.\n\n"
        "يدعم: YouTube • TikTok • Instagram • Facebook • X • Reddit • Pinterest • SoundCloud • Twitch وغيرها.\n\n"
        "📎 أرسل الرابط فقط، ثم اختر فيديو أو MP3 أو معلومات المقطع.\n\n"
        "<i>استخدم البوت فقط للمحتوى الذي يحق لك تنزيله. لا يدعم المحتوى الخاص أو المحمي بـ DRM.</i>"
    )


@router.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer("أرسل رابطًا عامًا من منصة مدعومة.\n/invite رابط الدعوة\n/help المساعدة")


@router.message(Command("invite"))
async def invite(m: Message):
    await app.db.upsert_user(m.from_user)
    username = app.username or (await app.bot.get_me()).username
    link = f"https://t.me/{username}?start=ref_{m.from_user.id}"
    await m.answer(f"🎁 رابط دعوتك:\n<code>{link}</code>\n\nكل شخص يدخل عبره يُسجل كإحالة لك.")


@router.callback_query(F.data == "check_sub")
async def check_sub(cb: CallbackQuery):
    if await is_subscribed(app.bot, cb.from_user.id, app.s.force_sub_channel):
        await cb.answer("تم ✅", show_alert=True)
        await cb.message.answer("✅ صار بإمكانك استخدام البوت. أرسل رابطًا.")
    else:
        await cb.answer("لسه ما ظهر اشتراكك.", show_alert=True)


@router.message(Command("stats"))
async def stats_cmd(m: Message):
    if m.from_user.id not in app.s.admins:
        return
    users, downloads, active = await app.db.stats()
    await m.answer(f"👥 المستخدمون: {users}\n⬇️ التنزيلات: {downloads}\n⚡ نشط 24 ساعة: {active}")


@router.message(Command("broadcast"))
async def broadcast(m: Message):
    if m.from_user.id not in app.s.admins:
        return
    text = m.text.partition(" ")[2].strip()
    if not text:
        await m.answer("استخدم: /broadcast النص")
        return
    ok = bad = 0
    for uid in await app.db.all_user_ids():
        try:
            await app.bot.send_message(uid, text)
            ok += 1
        except Exception:
            bad += 1
        await asyncio.sleep(0.035)
    await m.answer(f"تم الإرسال ✅ {ok} | فشل {bad}")


@router.message(F.text)
async def link_handler(m: Message):
    await app.db.upsert_user(m.from_user)
    if not await app.require_access(m.from_user.id, m):
        return
    if not app.limiter.allow(m.from_user.id):
        await m.answer("⏳ طلبات كثيرة بسرعة. جرّب بعد دقيقة.")
        return
    url = extract_url(m.text)
    if not url:
        await m.answer("📎 أرسل رابطًا من منصة مدعومة.")
        return
    if not is_safe_supported_url(url):
        await m.answer("❌ الرابط غير مدعوم حاليًا. جرّب YouTube/TikTok/Instagram/Facebook/X/Reddit/Pinterest/SoundCloud/Twitch/Vimeo.")
        return
    job_id = await app.db.make_job(m.from_user.id, url)
    await m.answer("اختر المطلوب 👇", reply_markup=download_keyboard(job_id))


async def send_cached(cb: CallbackQuery, row) -> bool:
    if not row:
        return False
    file_id, media_type, title = row
    caption = f"✅ {escape(title or 'جاهز')}"
    try:
        if media_type == "audio":
            await cb.message.answer_audio(file_id, caption=caption)
        else:
            await cb.message.answer_video(file_id, caption=caption, supports_streaming=True)
        return True
    except Exception:
        logger.warning("Cached Telegram file_id failed; falling back to a fresh download", exc_info=True)
        return False


@router.callback_query(F.data.startswith("dl:"))
async def download_cb(cb: CallbackQuery):
    if not await app.require_access(cb.from_user.id, cb):
        await cb.answer()
        return
    if not app.limiter.allow(cb.from_user.id):
        await cb.answer("طلبات كثيرة بسرعة. جرّب بعد دقيقة.", show_alert=True)
        return
    try:
        _, mode, job_id = cb.data.split(":", 2)
    except ValueError:
        return
    url = await app.db.get_job(job_id, cb.from_user.id)
    if not url:
        await cb.answer("انتهت صلاحية الرابط، أرسله مرة ثانية.", show_alert=True)
        return
    await cb.answer()

    if mode == "info":
        status = await cb.message.answer("🔎 عم جيب معلومات المقطع...")
        try:
            info = await app.downloader.info(url)
            text = (
                f"<b>{escape(str(info.get('title') or 'بدون عنوان'))}</b>\n"
                f"👤 {escape(str(info.get('uploader') or info.get('channel') or 'غير معروف'))}\n"
                f"⏱ {info.get('duration') or '؟'} ثانية\n"
                f"👁 {info.get('view_count') or '؟'}\n"
                f"📦 {human_size(info.get('filesize') or info.get('filesize_approx'))}"
            )
            await status.edit_text(text)
        except Exception:
            await status.edit_text("❌ ما قدرت أجيب المعلومات. قد يكون الرابط خاصًا أو المنصة غيّرت نظامها.")
        return

    if mode == "thumb":
        status = await cb.message.answer("🖼 عم جيب الصورة...")
        try:
            info = await app.downloader.info(url)
            thumb = info.get("thumbnail")
            if not thumb:
                raise RuntimeError("no thumbnail")
            async with aiohttp.ClientSession() as session:
                async with session.get(thumb, timeout=20) as r:
                    r.raise_for_status()
                    if r.content_length and r.content_length > 10 * 1024 * 1024:
                        raise RuntimeError("thumbnail too large")
                    data = await r.read()
                    if len(data) > 10 * 1024 * 1024:
                        raise RuntimeError("thumbnail too large")
            await cb.message.answer_photo(BufferedInputFile(data, filename="thumbnail.jpg"))
            await status.delete()
        except Exception:
            await status.edit_text("❌ ما لقيت صورة للمحتوى.")
        return

    if mode not in {"video", "audio"}:
        return
    key = cache_key(url, mode)
    if await send_cached(cb, await app.db.get_cache(key)):
        await app.db.count_download(cb.from_user.id)
        return

    status = await cb.message.answer("⬇️ عم نزّل وأجهّز الملف... ممكن ياخذ شوي حسب الحجم.")
    result = None
    try:
        result = await app.downloader.download(url, mode)
        if not result.path or not Path(result.path).exists():
            raise RuntimeError("download missing")
        size = Path(result.path).stat().st_size
        if size > app.s.max_file_mb * 1024 * 1024:
            await status.edit_text(f"⚠️ الملف حجمه {human_size(size)} وأكبر من الحد المضبوط للبوت ({app.s.max_file_mb} MB). جرّب MP3 أو مقطع أصغر.")
            return
        caption = f"✅ <b>{escape(result.title[:180])}</b>\n⚡ @{app.username}"
        file = FSInputFile(result.path)
        if mode == "audio":
            sent = await cb.message.answer_audio(file, caption=caption, title=result.title[:64])
            file_id = sent.audio.file_id
        else:
            sent = await cb.message.answer_video(file, caption=caption, supports_streaming=True)
            file_id = sent.video.file_id
        await app.db.set_cache(key, file_id, mode, result.title)
        await app.db.count_download(cb.from_user.id)
        await status.delete()
    except Exception:
        logger.exception("Download failed for user=%s", cb.from_user.id)
        await status.edit_text("❌ فشل التنزيل. غالبًا الرابط خاص/محذوف، أو المنصة تحتاج تحديث yt-dlp. جرّب رابطًا آخر.")
    finally:
        if result:
            app.downloader.cleanup(result.path)


async def build_bot(settings: Settings) -> tuple[Bot, Dispatcher]:
    global app
    settings.ensure_dirs()
    app = App(settings)
    await app.db.init()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    app.bot = bot
    app.username = (await bot.get_me()).username or ""
    dp = Dispatcher()
    dp.include_router(router)
    return bot, dp
