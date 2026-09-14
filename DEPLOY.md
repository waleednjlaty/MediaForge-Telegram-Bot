# Deployment

## Railway / Render / VPS

أسهل نشر دائم هو Docker.

1. أنشئ Bot من `@BotFather` واحصل على `BOT_TOKEN`.
2. ضع متغيرات `.env` في خدمة الاستضافة، ولا ترفع `.env` إلى GitHub.
3. شغّل Dockerfile كما هو.
4. إذا فعّلت `FORCE_SUB_CHANNEL`، أضف البوت Admin إلى القناة حتى يستطيع التحقق من العضوية.

### VPS

```bash
git clone <repo-url>
cd MediaForge-Telegram-Bot
cp .env.example .env
nano .env
docker compose up -d --build
docker compose logs -f
```

### التحديثات

لأن المنصات تغيّر أنظمتها كثيرًا، أهم صيانة دورية هي تحديث yt-dlp:

```bash
pip install -U yt-dlp
```

أو أعد بناء Docker image بعد تحديث `requirements.txt`.
