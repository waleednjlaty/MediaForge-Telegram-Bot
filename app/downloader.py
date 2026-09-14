import asyncio
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

    async def info(self, url: str) -> dict:
        async with self.sem:
            return await asyncio.to_thread(self._extract_info, url)

    def _extract_info(self, url: str) -> dict:
        opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    async def download(self, url: str, mode: str) -> MediaResult:
        async with self.sem:
            return await asyncio.to_thread(self._download_sync, url, mode)

    def _download_sync(self, url: str, mode: str) -> MediaResult:
        tmp = tempfile.mkdtemp(prefix="mediaforge_", dir="downloads")
        outtmpl = os.path.join(tmp, "%(title).80s-%(id)s.%(ext)s")
        base = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "outtmpl": outtmpl,
            "restrictfilenames": True,
            "max_filesize": self.max_bytes,
            "cachedir": False,
        }
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
            candidates.extend([filename, str(Path(filename).with_suffix(".mp4")), str(Path(filename).with_suffix(".mp3"))])
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
