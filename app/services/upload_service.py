from pathlib import Path
from typing import Protocol

from fastapi import UploadFile

from app.adapters.storage import Storage
from app.domain.models import UploadResponse


class UploadServiceProtocol(Protocol):
    async def store(self, cv: UploadFile, report: UploadFile) -> UploadResponse:
        ...


class UploadService(UploadServiceProtocol):
    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    async def store(self, cv: UploadFile, report: UploadFile) -> UploadResponse:
        cv_id = await self._storage.save_upload(cv)
        report_id = await self._storage.save_upload(report)
        return UploadResponse(cv_id=cv_id, report_id=report_id)
