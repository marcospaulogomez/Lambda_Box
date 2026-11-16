"""Adapt the existing desktop generator to portable, in-memory PNG output."""

from io import BytesIO
import unicodedata

from PIL import Image, ImageDraw, ImageFont
import qrcode
from qrcode.exceptions import DataOverflowError


MAX_TEXT_BYTES = 1200
MAX_CAPTION_LENGTH = 80


class QrCodeError(ValueError):
    """Invalid content or a QR Code that cannot fit the supported capacity."""


def generate_png(text: str, caption: str = "") -> bytes:
    if not isinstance(text, str) or not text.strip():
        raise QrCodeError("Digite um link ou texto para gerar o QR Code.")
    try:
        encoded = text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise QrCodeError("O conteúdo contém caracteres inválidos.") from exc
    if len(encoded) > MAX_TEXT_BYTES:
        raise QrCodeError(f"O conteúdo deve ter no máximo {MAX_TEXT_BYTES} bytes em UTF-8.")
    if not isinstance(caption, str) or len(caption) > MAX_CAPTION_LENGTH:
        raise QrCodeError(f"A legenda deve ter no máximo {MAX_CAPTION_LENGTH} caracteres.")
    if any(unicodedata.category(char) in {"Cc", "Cs"} for char in caption):
        raise QrCodeError("Use uma única linha de texto na legenda, sem caracteres de controle.")

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=8, border=4)
    qr.add_data(encoded, optimize=0)
    try:
        qr.make(fit=True)
    except DataOverflowError as exc:
        raise QrCodeError("O conteúdo excede a capacidade do QR Code.") from exc
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    caption = caption.strip()
    if caption:
        # Pillow bundles this font, so rendering never depends on Windows fonts.
        measure = ImageDraw.Draw(image)
        for size in range(26, 7, -1):
            font = ImageFont.load_default(size=size)
            box = measure.textbbox((0, 0), caption, font=font)
            if box[2] - box[0] <= image.width - 32:
                break
        if box[2] - box[0] > image.width - 32:
            raise QrCodeError("A legenda é larga demais. Use um texto mais curto.")
        result = Image.new("RGB", (image.width, image.height + box[3] - box[1] + 24), "white")
        result.paste(image, (0, 0))
        ImageDraw.Draw(result).text(((image.width - (box[2] - box[0])) / 2 - box[0], image.height + 8 - box[1]),
                                    caption, font=font, fill="black")
        image = result
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
