from app.utils import extract_url, is_safe_supported_url, cache_key


def test_extract_url():
    assert extract_url("hi https://youtu.be/abc123 ok") == "https://youtu.be/abc123"


def test_supported_url():
    assert is_safe_supported_url("https://www.instagram.com/reel/abc/")
    assert is_safe_supported_url("https://x.com/user/status/123")
    assert not is_safe_supported_url("http://127.0.0.1/test")
    assert not is_safe_supported_url("https://example.com/file")


def test_cache_key_stable():
    assert cache_key("https://youtu.be/x", "video") == cache_key("https://youtu.be/x", "video")
    assert cache_key("https://youtu.be/x", "video") != cache_key("https://youtu.be/x", "audio")
