import hashlib
import ipaddress
import re
from urllib.parse import urlparse

URL_RE = re.compile(r"https?://[^\s]+", re.I)

ALLOWED_DOMAINS = {
    "youtube.com", "youtu.be", "m.youtube.com", "music.youtube.com",
    "tiktok.com", "www.tiktok.com", "vm.tiktok.com", "vt.tiktok.com",
    "instagram.com", "www.instagram.com",
    "facebook.com", "www.facebook.com", "fb.watch", "m.facebook.com",
    "twitter.com", "www.twitter.com", "x.com", "www.x.com",
    "reddit.com", "www.reddit.com", "redd.it", "v.redd.it",
    "pinterest.com", "www.pinterest.com", "pin.it",
    "soundcloud.com", "www.soundcloud.com",
    "twitch.tv", "www.twitch.tv", "clips.twitch.tv",
    "vimeo.com", "www.vimeo.com",
    "dailymotion.com", "www.dailymotion.com", "dai.ly",
}


def extract_url(text: str) -> str | None:
    m = URL_RE.search(text or "")
    return m.group(0).rstrip(".,)]}>") if m else None


def is_safe_supported_url(url: str) -> bool:
    try:
        p = urlparse(url)
        if p.scheme not in {"http", "https"} or not p.hostname:
            return False
        host = p.hostname.lower().rstrip(".")
        try:
            ip = ipaddress.ip_address(host)
            return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)
        except ValueError:
            pass
        return host in ALLOWED_DOMAINS or any(host.endswith("." + d) for d in ALLOWED_DOMAINS)
    except Exception:
        return False


def cache_key(url: str, mode: str) -> str:
    return hashlib.sha256(f"{mode}|{url}".encode()).hexdigest()


def human_size(n: int | float | None) -> str:
    if not n:
        return "غير معروف"
    size = float(n)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
