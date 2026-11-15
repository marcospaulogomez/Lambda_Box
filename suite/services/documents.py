"""Bounded local task queue and ownership of temporary files."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
import logging
from pathlib import Path
import re
import shutil
import tempfile
import threading
import time
import uuid
import zipfile
from typing import BinaryIO

from suite.conversion import ConversionError, LibreOfficeConverter, validate_docx
from suite.pdf import PdfProcessingError, merge_pdfs, validate_pdf
from suite.settings import Settings


logger = logging.getLogger(__name__)
TERMINAL_STATES = {"completed", "failed"}
OPERATIONS = {"word-to-pdf": {".docx"}, "merge-pdfs": {".pdf"}, "convert-and-merge": {".docx", ".pdf"}}


class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def safe_filename(filename: str | None, extensions: set[str] | None = None) -> str:
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "_", name).strip(" .")
    extension = Path(name).suffix.lower()
    if extension not in (extensions or {".docx"}):
        formats = ", ".join(sorted(extensions or {".docx"}))
        raise ServiceError(f"Formatos aceitos nesta ferramenta: {formats}.")
    return (Path(name).stem[:120] or "document") + extension


@dataclass
class Job:
    id: str
    directory: Path
    operation: str = "word-to-pdf"
    state: str = "uploading"
    filenames: list[str] = field(default_factory=list)
    outputs: list[Path] = field(default_factory=list)
    output_names: list[str] = field(default_factory=list)
    pages: int | None = None
    error: str | None = None
    seconds: float | None = None
    finished_at: float | None = None
    readers: int = 0


class DocumentService:
    """Single-process queue: one conversion at a time, isolated profile per job."""

    def __init__(self, settings: Settings, converter: LibreOfficeConverter):
        self.settings = settings
        self.converter = converter
        self._temporary = tempfile.TemporaryDirectory(prefix="suite-session-")
        self.root = Path(self._temporary.name)
        self._jobs: dict[str, Job] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="suite-conversion")

    def create(self, operation: str = "word-to-pdf") -> Job:
        if operation not in OPERATIONS:
            raise ServiceError("Ferramenta não encontrada.", 404)
        with self._lock:
            active = sum(job.state not in TERMINAL_STATES for job in self._jobs.values())
            if active >= self.settings.max_pending_jobs:
                raise ServiceError("A fila está cheia. Aguarde uma conversão terminar e tente novamente.", 429)
            if operation == "word-to-pdf" and self.converter.executable is None:
                raise ServiceError("LibreOffice não encontrado no servidor. Confira a instalação e reinicie a suíte.", 503)
            job_id = uuid.uuid4().hex
            directory = self.root / job_id
            (directory / "inputs").mkdir(parents=True)
            job = Job(job_id, directory, operation=operation)
            self._jobs[job_id] = job
            return job

    def submit(self, job: Job, filenames: list[str]) -> dict:
        sources = sorted((job.directory / "inputs").iterdir())
        if any(path.suffix == ".docx" for path in sources) and self.converter.executable is None:
            raise ServiceError("LibreOffice não encontrado no servidor para converter os documentos Word.", 503)
        page_count = 0
        for index, source in enumerate(sources, 1):
            try:
                if source.suffix == ".docx":
                    validate_docx(source)
                else:
                    page_count += validate_pdf(source, self.settings.max_pdf_pages)
                    if page_count > self.settings.max_pdf_pages:
                        raise PdfProcessingError(f"O limite desta etapa é de {self.settings.max_pdf_pages} páginas no total.")
            except (ConversionError, PdfProcessingError) as exc:
                raise ServiceError(f"Documento {index}: {exc}") from exc
        with self._lock:
            job.filenames = filenames
            job.state = "queued"
            self._executor.submit(self._convert, job, sources)
            return self.snapshot(job.id)

    def save_sources(self, job: Job, uploads: list[tuple[str | None, BinaryIO]]) -> list[str]:
        minimum = 1 if job.operation == "word-to-pdf" else 2
        if len(uploads) < minimum or len(uploads) > self.settings.max_files:
            raise ServiceError(f"Selecione de {minimum} a {self.settings.max_files} documentos.")
        filenames = []
        total_bytes = 0
        for index, (filename, stream) in enumerate(uploads, 1):
            name = safe_filename(filename, OPERATIONS[job.operation])
            filenames.append(name)
            file_bytes = 0
            with (job.directory / "inputs" / f"document-{index:03d}{Path(name).suffix}").open("xb") as target:
                while chunk := stream.read(64 * 1024):
                    file_bytes += len(chunk)
                    total_bytes += len(chunk)
                    if file_bytes > self.settings.max_file_bytes or total_bytes > self.settings.max_total_bytes:
                        raise ServiceError("Os arquivos excedem o limite de tamanho permitido.", 413)
                    target.write(chunk)
            if not file_bytes:
                raise ServiceError(f"O documento {index} está vazio.")
        return filenames

    def discard_upload(self, job: Job) -> None:
        with self._lock:
            self._jobs.pop(job.id, None)
            shutil.rmtree(job.directory)

    def _convert(self, job: Job, sources: list[Path]) -> None:
        with self._lock:
            job.state = "processing"
        error = None
        outputs = []
        output_names = []
        pages = None
        started = time.perf_counter()
        try:
            if job.operation == "word-to-pdf":
                result = self.converter.convert_batch(sources, job.directory / "outputs")
                outputs = list(result.outputs)
                output_names = [self.download_name(index, name) for index, name in enumerate(job.filenames, 1)]
            else:
                ordered_pdfs = sources
                docx_sources = [path for path in sources if path.suffix == ".docx"]
                if docx_sources:
                    converted = self.converter.convert_batch(docx_sources, job.directory / "converted")
                    conversions = dict(zip(docx_sources, converted.outputs))
                    ordered_pdfs = [conversions[path] if path.suffix == ".docx" else path for path in sources]
                merged = merge_pdfs(ordered_pdfs, job.directory / "outputs" / "merged.pdf", self.settings.max_pdf_pages)
                outputs = [merged.output]
                output_names = ["merged.pdf"]
                pages = merged.pages
            seconds = round(time.perf_counter() - started, 3)
            if len(outputs) > 1:
                with zipfile.ZipFile(job.directory / "documents.zip", "x", zipfile.ZIP_DEFLATED) as archive:
                    for path, name in zip(outputs, output_names):
                        archive.write(path, name)
        except (ConversionError, PdfProcessingError) as exc:
            error = str(exc)
        except Exception:
            logger.exception("Conversion failed for job %s", job.id)
            error = "Não foi possível concluir a conversão. Tente novamente com outro documento."
        finally:
            shutil.rmtree(job.directory / "inputs", ignore_errors=True)
            shutil.rmtree(job.directory / "converted", ignore_errors=True)
        with self._lock:
            if error:
                job.error = error
                job.state = "failed"
            else:
                job.outputs = outputs
                job.output_names = output_names
                job.pages = pages
                job.seconds = seconds
                job.state = "completed"
            job.finished_at = time.time()

    @staticmethod
    def download_name(index: int, filename: str) -> str:
        return f"{index:03d}-{Path(filename).stem}.pdf"

    def _get(self, job_id: str) -> Job:
        job = self._jobs.get(job_id)
        if job is None:
            raise ServiceError("Esta tarefa não existe ou seus arquivos já foram removidos.", 404)
        if job.finished_at is not None and time.time() - job.finished_at >= self.settings.retention_seconds:
            if not job.readers:
                self._remove(job)
            raise ServiceError("O prazo para download terminou. Envie os documentos novamente.", 410)
        return job

    def snapshot(self, job_id: str) -> dict:
        with self._lock:
            job = self._get(job_id)
            files = []
            if job.state == "completed":
                files = [{"name": job.output_names[index - 1],
                          "url": f"/api/jobs/{job.id}/files/{index}", "bytes": path.stat().st_size}
                         for index, path in enumerate(job.outputs, 1)]
            return {"id": job.id, "operation": job.operation, "state": job.state, "error": job.error, "seconds": job.seconds, "pages": job.pages,
                    "files": files, "expires_at": job.finished_at + self.settings.retention_seconds if job.finished_at else None,
                    "archive_url": f"/api/jobs/{job.id}/archive" if len(files) > 1 else None}

    @contextmanager
    def download(self, job_id: str, file_index: int | None = None):
        with self._lock:
            job = self._get(job_id)
            if job.state != "completed":
                raise ServiceError("Os arquivos desta tarefa ainda não estão disponíveis.", 409)
            if file_index is None:
                if len(job.outputs) < 2:
                    raise ServiceError("Este resultado não possui um arquivo ZIP.", 404)
                path, filename = job.directory / "documents.zip", "documentos-convertidos.zip"
            else:
                if file_index < 1 or file_index > len(job.outputs):
                    raise ServiceError("Arquivo não encontrado.", 404)
                path = job.outputs[file_index - 1]
                filename = job.output_names[file_index - 1]
            job.readers += 1
        try:
            yield path, filename
        finally:
            with self._lock:
                job.readers -= 1

    def _remove(self, job: Job) -> None:
        shutil.rmtree(job.directory)
        self._jobs.pop(job.id, None)

    def delete(self, job_id: str) -> None:
        with self._lock:
            job = self._get(job_id)
            if job.state not in TERMINAL_STATES or job.readers:
                raise ServiceError("A tarefa está em uso. Aguarde o processamento ou download terminar.", 409)
            self._remove(job)

    def cleanup(self) -> None:
        with self._lock:
            for job in list(self._jobs.values()):
                if job.finished_at is not None and not job.readers and time.time() - job.finished_at >= self.settings.retention_seconds:
                    self._remove(job)

    def close(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)
        self._temporary.cleanup()
