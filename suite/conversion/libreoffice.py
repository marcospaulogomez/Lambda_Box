"""Conversão local de DOCX com perfil descartável e prazo de execução."""

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import zipfile


class ConversionError(RuntimeError):
    """Falha que pode ser apresentada ao usuário sem uma pilha de chamadas."""


@dataclass(frozen=True)
class ConversionResult:
    output: Path
    seconds: float
    size_bytes: int
    timings: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class BatchConversionResult:
    outputs: tuple[Path, ...]
    seconds: float


def validate_docx(source: Path) -> None:
    """Check the package without changing the document or extracting its entries."""
    if not source.is_file() or source.suffix.lower() != ".docx":
        raise ConversionError("Selecione um arquivo DOCX existente.")
    try:
        with zipfile.ZipFile(source) as package:
            required = {"[Content_Types].xml", "word/document.xml"}
            if not required.issubset(package.namelist()):
                raise ConversionError("O arquivo não contém um documento DOCX reconhecível.")
            if any(entry.flag_bits & 1 for entry in package.infolist()):
                raise ConversionError("Documentos protegidos por senha não são aceitos nesta etapa.")
            if len(package.infolist()) > 2000 or sum(entry.file_size for entry in package.infolist()) > 100 * 1024 * 1024:
                raise ConversionError("O conteúdo descompactado do DOCX excede o limite desta etapa.")
    except (zipfile.BadZipFile, OSError) as exc:
        raise ConversionError("O arquivo DOCX está inválido ou não pode ser lido.") from exc


def find_libreoffice(explicit: str | Path | None = None) -> Path | None:
    """Procura uma instalação existente; um caminho explícito não usa fallback."""
    configured = explicit if explicit is not None else os.environ.get("LIBREOFFICE_PATH")
    if configured:
        candidate = Path(configured).expanduser()
        return candidate.resolve() if candidate.is_file() else None

    for name in ("soffice.com", "soffice", "libreoffice", "soffice.exe"):
        found = shutil.which(name)
        if found:
            return Path(found).resolve()

    for variable in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        root = os.environ.get(variable)
        if root:
            for binary in ("soffice.com", "soffice.exe"):
                candidate = Path(root) / "LibreOffice" / "program" / binary
                if candidate.is_file():
                    return candidate.resolve()
    candidate = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    return candidate if candidate.is_file() else None


def _execute(command: list[str], timeout: float) -> subprocess.CompletedProcess:
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", **options,
        )
    except OSError as exc:
        raise ConversionError(f"Não foi possível iniciar o LibreOffice: {exc}") from exc
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        # Encerra apenas a árvore desta execução, que possui perfil exclusivo.
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW,
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.poll() is None:
            process.kill()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        raise ConversionError(f"A conversão excedeu o limite de {timeout:g} segundos.") from exc
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


class LibreOfficeConverter:
    def __init__(self, executable: str | Path | None = None, *, timeout: float = 90):
        if timeout <= 0:
            raise ValueError("O prazo deve ser maior que zero.")
        self.executable = find_libreoffice(executable)
        self.timeout = timeout

    def version(self) -> str:
        if self.executable is None:
            raise ConversionError("LibreOffice não encontrado. Instale-o ou informe LIBREOFFICE_PATH.")
        result = _execute([str(self.executable), "--version"], min(self.timeout, 15))
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()[-1500:] or f"código de saída {result.returncode}"
            raise ConversionError(f"Falha ao consultar a versão: {detail}")
        return result.stdout.strip() or result.stderr.strip() or "Versão não informada"

    def convert_batch(self, sources: list[Path], output_dir: Path) -> BatchConversionResult:
        """Convert one task with one engine invocation; publish only a complete batch."""
        if not sources:
            raise ConversionError("Selecione pelo menos um documento.")
        sources = [Path(source).resolve() for source in sources]
        for source in sources:
            validate_docx(source)
        if self.executable is None:
            raise ConversionError("LibreOffice não encontrado. Instale-o ou informe LIBREOFFICE_PATH.")
        output_dir = Path(output_dir).resolve()
        destinations = tuple(output_dir / f"document-{index:03d}.pdf" for index in range(1, len(sources) + 1))
        if any(path.exists() for path in destinations):
            raise ConversionError("Já existe um resultado para este lote.")
        started = time.perf_counter()
        published = []
        with tempfile.TemporaryDirectory(prefix="suite-batch-") as temporary:
            work = Path(temporary)
            converted_dir = work / "pdf"
            converted_dir.mkdir()
            inputs = []
            for index, source in enumerate(sources, 1):
                copied = work / f"document-{index:03d}.docx"
                shutil.copyfile(source, copied)
                inputs.append(copied)
            result = _execute([
                str(self.executable), f"-env:UserInstallation={(work / 'profile').as_uri()}",
                "--headless", "--nologo", "--nodefault", "--norestore",
                "--convert-to", "pdf:writer_pdf_Export", "--outdir", str(converted_dir),
                *(str(path) for path in inputs),
            ], self.timeout)
            if result.returncode:
                raise ConversionError("O LibreOffice não concluiu o lote. Confira os documentos e tente novamente.")
            generated = [converted_dir / path.name for path in destinations]
            for index, path in enumerate(generated, 1):
                if not path.is_file():
                    raise ConversionError(f"O documento {index} não gerou PDF. Nenhum resultado do lote foi disponibilizado.")
                with path.open("rb") as stream:
                    if stream.read(5) != b"%PDF-":
                        raise ConversionError(f"O documento {index} não gerou um PDF válido.")
            output_dir.mkdir(parents=True, exist_ok=True)
            try:
                for source, destination in zip(generated, destinations):
                    with destination.open("xb") as target:
                        published.append(destination)
                        with source.open("rb") as stream:
                            shutil.copyfileobj(stream, target)
            except BaseException:
                for path in published:
                    path.unlink(missing_ok=True)
                raise
        return BatchConversionResult(destinations, round(time.perf_counter() - started, 3))

    def convert(self, source: Path, output_dir: Path) -> ConversionResult:
        source = Path(source).resolve()
        if not source.is_file() or source.suffix.lower() != ".docx":
            raise ConversionError("Selecione um arquivo DOCX existente.")
        try:
            with zipfile.ZipFile(source) as package:
                if not {"[Content_Types].xml", "word/document.xml"}.issubset(package.namelist()):
                    raise ConversionError("O arquivo não contém um documento DOCX reconhecível.")
        except (zipfile.BadZipFile, OSError) as exc:
            raise ConversionError("O arquivo DOCX está inválido ou não pode ser lido.") from exc
        if self.executable is None:
            raise ConversionError("LibreOffice não encontrado. Instale-o ou informe LIBREOFFICE_PATH.")

        output_dir = Path(output_dir).resolve()
        destination = output_dir / f"{source.stem}.pdf"
        if destination.exists():
            raise ConversionError(f"Já existe um resultado com esse nome: {destination.name}")
        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="suite-conversao-") as temporary:
            work = Path(temporary)
            # Nomes internos constantes evitam interpretar nomes de uploads como opções.
            copied_source = work / "entrada.docx"
            shutil.copyfile(source, copied_source)
            converted_dir = work / "pdf"
            converted_dir.mkdir()
            engine_started = time.perf_counter()
            result = _execute([
                str(self.executable), f"-env:UserInstallation={(work / 'perfil').as_uri()}",
                "--headless", "--nologo", "--nodefault", "--norestore",
                "--convert-to", "pdf:writer_pdf_Export", "--outdir", str(converted_dir),
                str(copied_source),
            ], self.timeout)
            engine_finished = time.perf_counter()
            if result.returncode:
                detail = (result.stderr or result.stdout or "Sem detalhes adicionais").strip()[-1500:]
                raise ConversionError(f"O LibreOffice não concluiu a conversão (código {result.returncode}): {detail}")
            generated = converted_dir / "entrada.pdf"
            if not generated.is_file():
                raise ConversionError("O LibreOffice terminou sem gerar o PDF. Verifique o documento.")
            with generated.open("rb") as stream:
                if stream.read(5) != b"%PDF-":
                    raise ConversionError("O resultado gerado não tem um cabeçalho PDF válido.")
            output_dir.mkdir(parents=True, exist_ok=True)
            # Criação exclusiva também impede sobrescrita em uma disputa concorrente.
            with destination.open("xb") as target:
                try:
                    with generated.open("rb") as stream:
                        shutil.copyfileobj(stream, target)
                except BaseException:
                    target.close()
                    destination.unlink(missing_ok=True)
                    raise
            cleanup_started = time.perf_counter()
        finished = time.perf_counter()
        timings = {
            "preparacao": round(engine_started - started, 3),
            "motor": round(engine_finished - engine_started, 3),
            "publicacao": round(cleanup_started - engine_finished, 3),
            "limpeza": round(finished - cleanup_started, 3),
        }
        return ConversionResult(destination, round(finished - started, 3), destination.stat().st_size, timings)
