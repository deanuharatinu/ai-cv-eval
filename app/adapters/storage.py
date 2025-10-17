import asyncio
import hashlib
import os
from pathlib import Path
from typing import Protocol

from fastapi import UploadFile

from app.core.config import settings


class Storage(Protocol):
    async def save_upload(self, upload: UploadFile) -> str:
        ...

    async def open(self, file_id: str) -> bytes:
        ...


class LocalStorage(Storage):
    def __init__(self, root: Path | None = None) -> None:
        self._root = Path(root or settings.storage_root)
        self._root.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, upload: UploadFile) -> str:
        payload = await upload.read()
        digest = hashlib.sha256(payload).hexdigest()
        ext = Path(upload.filename or "").suffix or ".bin"
        file_id = digest[:32]
        target = self._root / f"{file_id}{ext}"
        await asyncio.to_thread(target.write_bytes, payload)
        return file_id

    async def open(self, file_id: str) -> bytes:
        candidates = list(self._root.glob(f"{file_id}*"))
        if not candidates:
            raise FileNotFoundError(file_id)
        path = candidates[0]
        return await asyncio.to_thread(path.read_bytes)
