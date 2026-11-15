"""Merge PDFs in the given order without rasterizing their pages."""

from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
import time

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError


class PdfProcessingError(Exception):
    pass


@dataclass(frozen=True)
class PdfMergeResult:
    output: Path
    pages: int
    seconds: float


def _read_pdf(stream, max_pages: int) -> PdfReader:
    if stream.read(5) != b"%PDF-":
        raise PdfProcessingError("O arquivo não tem um cabeçalho PDF válido.")
    stream.seek(0)
    reader = PdfReader(stream)
    if reader.is_encrypted:
        raise PdfProcessingError("PDFs protegidos por senha não são aceitos nesta etapa.")
    pages = len(reader.pages)
    if pages < 1:
        raise PdfProcessingError("O PDF não contém páginas.")
    if pages > max_pages:
        raise PdfProcessingError(f"O limite desta etapa é de {max_pages} páginas no total.")
    return reader


def validate_pdf(source: Path, max_pages: int = 500) -> int:
    try:
        with source.open("rb") as stream:
            return len(_read_pdf(stream, max_pages).pages)
    except (PyPdfError, ValueError, TypeError, RecursionError, OverflowError, OSError) as exc:
        raise PdfProcessingError("Não foi possível ler o PDF. Confira se o arquivo está íntegro.") from exc


def merge_pdfs(sources: list[Path], destination: Path, max_pages: int = 500) -> PdfMergeResult:
    if not sources:
        raise PdfProcessingError("Selecione PDFs para juntar.")
    if destination.exists():
        raise PdfProcessingError("Já existe um resultado para esta tarefa.")
    started = time.perf_counter()
    writer = PdfWriter()
    created = False
    try:
        with ExitStack() as stack:
            total_pages = 0
            for index, source in enumerate(sources, 1):
                try:
                    reader = _read_pdf(stack.enter_context(source.open("rb")), max_pages)
                    total_pages += len(reader.pages)
                    if total_pages > max_pages:
                        raise PdfProcessingError(f"O limite desta etapa é de {max_pages} páginas no total.")
                    # Avoid collisions when two inputs have fields with the same name.
                    reader.add_form_topname(f"document_{index}")
                    writer.append(reader)
                except PdfProcessingError as exc:
                    raise PdfProcessingError(f"Documento {index}: {exc}") from exc
                except (PyPdfError, ValueError, TypeError, RecursionError, OverflowError, OSError) as exc:
                    raise PdfProcessingError(f"Não foi possível juntar o documento {index}. Confira a integridade do PDF.") from exc
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                created = True
                writer.write(stream)
        return PdfMergeResult(destination, total_pages, round(time.perf_counter() - started, 3))
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise
    finally:
        writer.close()
