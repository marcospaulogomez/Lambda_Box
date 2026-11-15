"""Place each decoded image on its own A4 page without cropping or resampling."""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile
import time
import warnings

from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas


class ImageProcessingError(Exception):
    pass


@dataclass(frozen=True)
class ImagePdfResult:
    output: Path
    pages: int
    seconds: float


@contextmanager
def _decoded_image(source: Path, max_pixels: int, remaining_pixels: int | None = None):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source, formats=["JPEG", "PNG"]) as image:
                expected = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG"}.get(source.suffix.lower())
                if image.format != expected:
                    raise ImageProcessingError("O conteúdo da imagem não corresponde à extensão JPG, JPEG ou PNG.")
                if getattr(image, "n_frames", 1) != 1:
                    raise ImageProcessingError("Imagens animadas não são aceitas nesta etapa. Envie uma imagem estática.")
                if image.mode not in {"1", "L", "LA", "P", "PA", "RGB", "RGBA", "CMYK", "YCbCr"}:
                    raise ImageProcessingError("Esta etapa aceita imagens de até 8 bits por canal. Converta a imagem antes de enviar.")
                pixels = image.width * image.height
                if pixels < 1 or pixels > max_pixels:
                    raise ImageProcessingError(f"A imagem excede o limite de {max_pixels:,} pixels por arquivo.".replace(",", "."))
                if remaining_pixels is not None and pixels > remaining_pixels:
                    raise ImageProcessingError("A soma dos pixels das imagens excede o limite desta tarefa.")
                # Header inspection alone does not detect truncated pixel data.
                image.load()
                yield image
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageProcessingError("A imagem possui dimensões grandes demais para esta etapa.") from exc
    except (OSError, ValueError, SyntaxError) as exc:
        raise ImageProcessingError("Não foi possível ler a imagem. Confira se o JPG ou PNG está íntegro.") from exc


def validate_image(source: Path, max_pixels: int = 40_000_000, *, remaining_pixels: int | None = None) -> int:
    """Decode the supported format and return its pixel count without altering it."""
    with _decoded_image(source, max_pixels, remaining_pixels) as image:
        return image.width * image.height


@contextmanager
def _rgb_image(image: Image.Image):
    with ImageOps.exif_transpose(image) as oriented:
        if oriented.mode in {"RGBA", "LA"} or "transparency" in oriented.info:
            with oriented.convert("RGBA") as rgba, Image.new("RGB", oriented.size, "white") as background:
                with rgba.getchannel("A") as alpha:
                    background.paste(rgba, mask=alpha)
                yield background
        else:
            with oriented.convert("RGB") as rgb:
                yield rgb


def images_to_pdf(sources: list[Path], destination: Path, *, max_pixels: int = 40_000_000,
                  max_total_pixels: int = 100_000_000, max_pages: int = 500) -> ImagePdfResult:
    if not sources:
        raise ImageProcessingError("Selecione pelo menos uma imagem.")
    if len(sources) > max_pages:
        raise ImageProcessingError(f"O limite desta etapa é de {max_pages} páginas no total.")
    if destination.exists():
        raise ImageProcessingError("Já existe um resultado para esta tarefa.")
    started = time.perf_counter()
    total_pixels = 0
    with tempfile.TemporaryDirectory(prefix="suite-images-") as temporary:
        generated = Path(temporary) / "images.pdf"
        canvas = Canvas(str(generated), pagesize=A4, pageCompression=1)
        canvas.setTitle("Images to PDF")
        canvas.setCreator("Document Suite")
        for index, source in enumerate(sources, 1):
            try:
                with _decoded_image(source, max_pixels, max_total_pixels - total_pixels) as image:
                    total_pixels += image.width * image.height
                    with _rgb_image(image) as rgb:
                        page_width, page_height = landscape(A4) if rgb.width > rgb.height else A4
                        margin = 12 * mm
                        scale = min((page_width - 2 * margin) / rgb.width, (page_height - 2 * margin) / rgb.height)
                        width, height = rgb.width * scale, rgb.height * scale
                        canvas.setPageSize((page_width, page_height))
                        canvas.drawImage(ImageReader(rgb), (page_width - width) / 2, (page_height - height) / 2,
                                         width=width, height=height)
                        canvas.showPage()
            except ImageProcessingError as exc:
                raise ImageProcessingError(f"Imagem {index}: {exc}") from exc
        canvas.save()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as output:
            try:
                with generated.open("rb") as stream:
                    shutil.copyfileobj(stream, output)
            except BaseException:
                output.close()
                destination.unlink(missing_ok=True)
                raise
    return ImagePdfResult(destination, len(sources), round(time.perf_counter() - started, 3))
