import asyncio
import base64
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yt_dlp


@dataclass
class MediaResult:
    path: str | None
    title: str
    duration: int | None = None
    thumbnail: str | None = None
    uploader: str | None = None
    webpage_url: str | None = None
    filesize: int | None = None


class MediaDownloader:
    def __init__(self, max_file_mb: int, concurrency: int = 2):
        self.max_bytes = max_file_mb * 1024 * 1024
        self.sem = asyncio.Semaphore(concurrency)
        self.cookie_file = self._prepare_cookie_file()

    @staticmethod
    def _prepare_cookie_file() -> str | None:
        """Create a local Netscape cookie file from env when provided.

        Supported env vars:
        - YTDLP_COOKIES_PATH: path to an existing cookies.txt file
        - YTDLP_COOKIES_B64: base64-encoded contents of cookies.txt
        """
        existing = os.getenv("YTDLP_COOKIES_PATH", "").strip()
        if existing and os.path.isfile(existing):
            return existing

        encoded = os.getenv("YTDLP_COOKIES_B64", "").strip()
        if not encoded:
            return None

        try:
            raw = base64.b64decode(encoded, validate=True)
            cookie_dir = Path("data")
            cookie_dir.mkdir(parents=True, exist_ok=True)
            path = cookie_dir / "yt-dlp-cookies.txt"
            path.write_bytes(raw)
            return str(path)
        except Exception:
            return None

    def _common_opts(self) -> dict:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "cachedir": False,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        }
        if self.cookie_file:
            opts["cookiefile"] = self.cookie_file
        return opts

    async def info(self, url: str) -> dict:
        async with self.sem:
            return await asyncio.to_thread(self._extract_info, url)

    def _extract_info(self, url: str) -> dict:
        opts = self._common_opts()
        opts["skip_download"] = True
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    async def download(self, url: str, mode: str) -> MediaResult:
        async with self.sem:
            return await asyncio.to_thread(self._download_sync, url, mode)

    def _download_sync(self, url: str, mode: str) -> MediaResult:
        tmp = tempfile.mkdtemp(prefix="mediaforge_", dir="downloads")
        outtmpl = os.path.join(tmp, "%(title).80s-%(id)s.%(ext)s")
        base = self._common_opts()
        base.update({
            "outtmpl": outtmpl,
            "restrictfilenames": True,
            "max_filesize": self.max_bytes,
        })

        if mode == "audio":
            base.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })
        else:
            base.update({
                "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
                "merge_output_format": "mp4",
            })

        with yt_dlp.YoutubeDL(base) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title") or "media"
            requested = info.get("requested_downloads") or []
            candidates = []
            if requested:
                candidates.extend([x.get("filepath") for x in requested if x.get("filepath")])
            filename = ydl.prepare_filename(info)
            candidates.extend([
                filename,
                str(Path(filename).with_suffix(".mp4")),
                str(Path(filename).with_suffix(".mp3")),
            ])
            path = next((p for p in candidates if p and os.path.exists(p)), None)
            if not path:
                files = [str(p) for p in Path(tmp).glob("*") if p.is_file()]
                path = files[0] if files else None
            size = os.path.getsize(path) if path else None
            return MediaResult(
                path=path,
                title=title,
                duration=info.get("duration"),
                thumbnail=info.get("thumbnail"),
                uploader=info.get("uploader") or info.get("channel"),
                webpage_url=info.get("webpage_url") or url,
                filesize=size,
            )

    @staticmethod
    def cleanup(path: str | None) -> None:
        if not path:
            return
        try:
            shutil.rmtree(str(Path(path).parent), ignore_errors=True)
        except Exception:
            pass
