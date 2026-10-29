"""API-key authentication with two roles: uploader and reviewer. Fails closed if not configured."""
import hmac
import os

from fastapi import Header, HTTPException


def _same(a: str, b: str) -> bool:
    return bool(a) and bool(b) and hmac.compare_digest(a.encode(), b.encode())


def _reviewers() -> dict[str, str]:
    out = {}
    for pair in os.getenv("REVIEWERS", "").split(","):
        if ":" in pair:
            name, key = pair.split(":", 1)
            if name.strip() and key.strip():
                out[name.strip()] = key.strip()
    return out


def require_uploader(x_api_key: str = Header(default="")) -> str:
    if _same(x_api_key, os.getenv("UPLOAD_API_KEY", "")):
        return "uploader"
    raise HTTPException(401, "Invalid or missing API key")


def require_reviewer(x_api_key: str = Header(default="")) -> str:
    found = None
    for name, key in _reviewers().items():
        if _same(x_api_key, key):
            found = name
    if found:
        return found
    raise HTTPException(401, "Invalid or missing API key")