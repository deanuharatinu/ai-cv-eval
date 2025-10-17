from functools import lru_cache

from app.adapters.queue_inproc import InProcessQueue
from app.adapters.storage import LocalStorage, Storage
from app.services.eval_service import EvalService, EvalServiceProtocol
from app.services.upload_service import UploadService, UploadServiceProtocol
from app.infra.db import AsyncSessionMaker


@lru_cache
def get_storage() -> Storage:
    return LocalStorage()


@lru_cache
def get_queue() -> InProcessQueue:
    return InProcessQueue()


def get_upload_service() -> UploadServiceProtocol:
    return UploadService(storage=get_storage())


def get_eval_service() -> EvalServiceProtocol:
    return EvalService(queue=get_queue(), session_factory=AsyncSessionMaker)
