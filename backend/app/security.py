"""API Key 等敏感字段的本地加密（Fernet/AES-128-CBC + HMAC）。

密钥保存在数据目录 `.secret_key`，受操作系统用户目录权限保护；
应用不向任何外部服务上报密钥。
"""

from __future__ import annotations

import base64
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from .config import settings


@lru_cache
def _fernet() -> Fernet:
    path = settings.secret_key_path
    if path.exists():
        key = path.read_bytes().strip()
    else:
        key = base64.urlsafe_b64encode(os.urandom(32))
        path.write_bytes(key)
    return Fernet(key)


def encrypt(plaintext: str | None) -> str | None:
    if not plaintext:
        return None
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return None


def mask_secret(plaintext: str | None) -> str:
    """界面展示用掩码：sk-x****abcd。"""
    if not plaintext:
        return ""
    if len(plaintext) <= 8:
        return "*" * len(plaintext)
    return f"{plaintext[:4]}{'*' * (len(plaintext) - 8)}{plaintext[-4:]}"
