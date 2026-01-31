from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit


_REDACTION = "***redacted***"


def redact_url(url: str) -> str:
    """Redact any userinfo (username/password/token) from a URL."""
    try:
        parts = urlsplit(url)
    except Exception:
        return _redact_userinfo_fallback(url)

    if "@" not in parts.netloc:
        return url

    _, host = parts.netloc.rsplit("@", 1)
    safe_netloc = f"{_REDACTION}@{host}"
    return urlunsplit((parts.scheme, safe_netloc, parts.path, parts.query, parts.fragment))


def redact(text: str) -> str:
    """Best-effort redaction for secrets that may appear in logs."""
    if not text:
        return text

    # Redact userinfo in https URLs: https://user:pass@host/... or https://token@host/...
    text = re.sub(r"https?://[^\s/@]+@", f"https://{_REDACTION}@", text)
    text = re.sub(r"https?://[^\s/@]+:[^\s/@]+@", f"https://{_REDACTION}@", text)

    # Redact common GitHub token formats if they appear standalone.
    text = re.sub(r"\bghp_[A-Za-z0-9]{20,}\b", _REDACTION, text)
    text = re.sub(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b", _REDACTION, text)

    return text


def _redact_userinfo_fallback(url: str) -> str:
    if "@" not in url:
        return url
    # Replace anything between scheme:// and @
    return re.sub(r"(https?://)([^\s/@]+@)", rf"\1{_REDACTION}@", url)
