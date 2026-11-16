"""Static, open-amount Pix BR Code per Banco Central's published layout."""

from binascii import crc_hqx
import re
import unicodedata


class PixConfigurationError(ValueError):
    """Missing or invalid public donation configuration."""


def merchant_text(value: str, limit: int) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^A-Za-z0-9 .\-]", " ", value)
    return " ".join(value.split())[:limit].rstrip()


def pix_payload(key: str, recipient: str, city: str) -> str:
    """Omit amount and use *** as txid, so the donor chooses the amount."""
    key = key.strip()
    valid_key = (re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", key)
                 or re.fullmatch(r"\+[1-9][0-9]{1,14}", key)
                 or re.fullmatch(r"(?:[0-9]{11}|[0-9]{14})", key)
                 or re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", key))
    if not valid_key or len(key) > 77:
        raise PixConfigurationError("Configure PIX_KEY com uma chave Pix válida.")
    recipient = merchant_text(recipient, 25)
    city = merchant_text(city, 15)
    if not recipient or not city:
        raise PixConfigurationError("Configure PIX_RECIPIENT_NAME e PIX_RECIPIENT_CITY para gerar o QR Pix.")

    def field(identifier: str, value: str) -> str:
        return f"{identifier}{len(value):02d}{value}"

    account = field("00", "br.gov.bcb.pix") + field("01", key)
    payload = (field("00", "01") + field("26", account) + field("52", "0000") + field("53", "986")
               + field("58", "BR") + field("59", recipient) + field("60", city) + field("62", field("05", "***")) + "6304")
    return payload + f"{crc_hqx(payload.encode('ascii'), 0xFFFF):04X}"
