"""Local defaults; public hosting limits will be measured separately."""

from dataclasses import dataclass
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    max_files: int = 10
    max_file_bytes: int = 20 * 1024 * 1024
    max_total_bytes: int = 50 * 1024 * 1024
    max_pending_jobs: int = 4
    retention_seconds: int = 30 * 60
    conversion_timeout: float = 180
    max_pdf_pages: int = 500
    libreoffice_path: str | Path | None = None

    @classmethod
    def local(cls) -> "Settings":
        extracted = PROJECT_ROOT / "laboratory" / "engine" / "program" / "soffice.com"
        configured = os.environ.get("LIBREOFFICE_PATH")
        return cls(libreoffice_path=configured or (extracted if extracted.is_file() else None))
