# ⚡ MediaForge Telegram Bot

بوت تيليجرام عملي لتنزيل **المحتوى العام** من أشهر منصات السوشال ميديا وتحويل الصوت إلى MP3، مع كاش Telegram لتقليل إعادة التنزيل، Referral، إحصائيات، Broadcast، Rate Limiting، واشتراك إجباري اختياري.

## لماذا هذه الفكرة؟

خدمة تنزيل الروابط من أكثر أنواع البوتات استخدامًا لأنها تحل مشكلة مباشرة: المستخدم يرسل رابطًا ويأخذ الملف داخل Telegram بدون مواقع مليانة إعلانات. بدل أن يكون مجرد Downloader، MediaForge يعطي أيضًا معلومات المقطع، الصورة المصغرة، استخراج MP3، وكاش يعيد نفس الملف فورًا إذا طلبه مستخدم آخر.

## المنصات

YouTube, TikTok, Instagram, Facebook, X/Twitter, Reddit, Pinterest, SoundCloud, Twitch, Vimeo, Dailymotion.

> يعتمد على `yt-dlp`، لذلك دعم المواقع يتغير مع تحديث المنصات. حدّث yt-dlp باستمرار.

## الميزات

- فيديو حتى 720p
- استخراج MP3
- Thumbnail
- معلومات المقطع
- Telegram `file_id` cache
- Referral deep links
- Admin stats
- Admin broadcast
- Rate limiting
- Forced subscription اختياري
- SQLite بدون إعداد خارجي
- Docker + ffmpeg
- GitHub Actions tests
- حماية أساسية من روابط localhost/private IP

## التشغيل المحلي

```bash
cp .env.example .env
# ضع BOT_TOKEN و ADMIN_IDS
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

يجب تثبيت `ffmpeg` على الجهاز.

## Docker

```bash
cp .env.example .env
docker compose up -d --build
```

## متغيرات البيئة

- `BOT_TOKEN`: توكن BotFather
- `ADMIN_IDS`: آيدي الأدمن، ويمكن أكثر من واحد بفواصل
- `MAX_FILE_MB`: افتراضي 49MB لترك هامش آمن
- `DOWNLOAD_CONCURRENCY`: عدد التنزيلات المتزامنة
- `FORCE_SUB_CHANNEL`: مثال `@YourChannel` أو اتركه فارغًا
- `FORCE_SUB_JOIN_URL`: رابط الاشتراك

## أوامر BotFather المقترحة

```text
start - تشغيل البوت
help - طريقة الاستخدام
invite - رابط دعوتك
```

أوامر الأدمن غير المعلنة:

```text
/stats
/broadcast النص
```

## سياسة الاستخدام

هذا المشروع مخصص لتنزيل المحتوى العام الذي يملك المستخدم حق تنزيله. لا يحاول تجاوز DRM أو المحتوى الخاص أو أنظمة الدفع. مسؤولية احترام حقوق النشر وشروط المنصة تقع على المستخدم والمشغّل.
