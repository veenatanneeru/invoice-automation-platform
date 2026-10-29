import pytest
from fastapi import HTTPException

from app import auth


def test_fails_closed_when_no_keys_configured(monkeypatch):
    monkeypatch.delenv("UPLOAD_API_KEY", raising=False)
    monkeypatch.delenv("REVIEWERS", raising=False)
    with pytest.raises(HTTPException):
        auth.require_uploader("")
    with pytest.raises(HTTPException):
        auth.require_reviewer("")


def test_roles_are_separate(monkeypatch):
    monkeypatch.setenv("UPLOAD_API_KEY", "up-key")
    monkeypatch.setenv("REVIEWERS", "alice:rev-key")
    assert auth.require_uploader("up-key") == "uploader"
    assert auth.require_reviewer("rev-key") == "alice"
    with pytest.raises(HTTPException):
        auth.require_reviewer("up-key")
    with pytest.raises(HTTPException):
        auth.require_uploader("rev-key")
    with pytest.raises(HTTPException):
        auth.require_uploader("wrong")