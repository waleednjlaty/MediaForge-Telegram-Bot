import time
import secrets
import aiosqlite


class Database:
    def __init__(self, path: str):
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at INTEGER NOT NULL,
                referred_by INTEGER,
                downloads INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS pending_links (
                job_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cache (
                cache_key TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                media_type TEXT NOT NULL,
                title TEXT,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            """)
            await db.commit()

    async def upsert_user(self, user, referred_by: int | None = None) -> None:
        now = int(time.time())
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                INSERT INTO users(user_id, username, first_name, joined_at, referred_by)
                VALUES(?,?,?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name
            """, (user.id, user.username, user.first_name, now, referred_by if referred_by != user.id else None))
            await db.commit()

    async def make_job(self, user_id: int, url: str) -> str:
        job_id = secrets.token_urlsafe(6).replace("-", "a").replace("_", "b")[:8]
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO pending_links(job_id,user_id,url,created_at) VALUES(?,?,?,?)",
                             (job_id, user_id, url, int(time.time())))
            await db.execute("DELETE FROM pending_links WHERE created_at < ?", (int(time.time()) - 3600,))
            await db.commit()
        return job_id

    async def get_job(self, job_id: str, user_id: int) -> str | None:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT url FROM pending_links WHERE job_id=? AND user_id=?", (job_id, user_id))
            row = await cur.fetchone()
            return row[0] if row else None

    async def get_cache(self, key: str):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT file_id, media_type, title FROM cache WHERE cache_key=?", (key,))
            return await cur.fetchone()

    async def set_cache(self, key: str, file_id: str, media_type: str, title: str = "") -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT OR REPLACE INTO cache(cache_key,file_id,media_type,title,created_at) VALUES(?,?,?,?,?)",
                             (key, file_id, media_type, title, int(time.time())))
            await db.commit()

    async def count_download(self, user_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET downloads=downloads+1 WHERE user_id=?", (user_id,))
            await db.execute("INSERT INTO events(user_id,event,created_at) VALUES(?,?,?)", (user_id, "download", int(time.time())))
            await db.commit()

    async def stats(self) -> tuple[int, int, int]:
        now = int(time.time())
        async with aiosqlite.connect(self.path) as db:
            users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
            downloads = (await (await db.execute("SELECT COALESCE(SUM(downloads),0) FROM users")).fetchone())[0]
            active = (await (await db.execute("SELECT COUNT(DISTINCT user_id) FROM events WHERE created_at>?", (now-86400,))).fetchone())[0]
        return users, downloads, active

    async def all_user_ids(self) -> list[int]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT user_id FROM users")
            return [row[0] for row in await cur.fetchall()]
