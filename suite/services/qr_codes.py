"""Bound QR generation independently from the document processing queue."""

from threading import BoundedSemaphore

from suite.qr.generation import QrCodeError, generate_png
from suite.services.documents import ServiceError


class QrCodeService:
    def __init__(self):
        self.slots = BoundedSemaphore(2)

    def generate(self, text: str, caption: str = "") -> bytes:
        if not self.slots.acquire(blocking=False):
            raise ServiceError("O gerador está ocupado. Tente novamente em instantes.", 429)
        try:
            return generate_png(text, caption)
        except QrCodeError as exc:
            raise ServiceError(str(exc)) from exc
        finally:
            self.slots.release()
