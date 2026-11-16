"""Explicit public contact settings; never expose the environment to templates."""

from dataclasses import dataclass
import os
from pathlib import Path
import re
from urllib.parse import quote, urlsplit

from dotenv import dotenv_values

from suite.payments.pix import PixConfigurationError, pix_payload
from suite.settings import PROJECT_ROOT


def https_url(value: str) -> str:
    if not value or any(char.isspace() or ord(char) < 32 for char in value):
        return ""
    try:
        parsed = urlsplit(value)
        if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password:
            parsed.port  # Validate malformed port values before rendering a link.
            return value
    except ValueError:
        pass
    return ""


@dataclass(frozen=True)
class SiteSettings:
    whatsapp: str = ""
    email: str = ""
    website: str = ""
    instagram: str = ""
    youtube: str = ""
    donation_url: str = ""
    pix_key: str = ""
    pix_recipient_name: str = ""
    pix_recipient_city: str = ""
    pix_bank_name: str = ""
    repository_url: str = ""

    @classmethod
    def local(cls, env_file: Path | None = None) -> "SiteSettings":
        values = {**dotenv_values(env_file or PROJECT_ROOT / ".env", interpolate=False), **os.environ}

        def public_value(name: str, limit: int = 300) -> str:
            value = (values.get(name) or "").strip()
            return value if len(value) <= limit and not any(ord(char) < 32 for char in value) else ""

        phone = public_value("CONTACT_WHATSAPP")
        phone = re.sub(r"[+()\s-]", "", phone)
        email = public_value("CONTACT_EMAIL")
        return cls(
            whatsapp=phone if re.fullmatch(r"[1-9][0-9]{9,14}", phone) else "",
            email=email if re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", email) else "",
            website=https_url(public_value("CONTACT_WEBSITE")),
            instagram=https_url(public_value("CONTACT_INSTAGRAM")),
            youtube=https_url(public_value("CONTACT_YOUTUBE")),
            donation_url=https_url(public_value("DONATION_URL")),
            pix_key=public_value("PIX_KEY", 140),
            pix_recipient_name=public_value("PIX_RECIPIENT_NAME", 100),
            pix_recipient_city=public_value("PIX_RECIPIENT_CITY", 100),
            pix_bank_name=public_value("PIX_BANK_NAME", 100),
            repository_url=https_url(public_value("PROJECT_REPOSITORY_URL")),
        )

    @property
    def whatsapp_url(self) -> str:
        message = quote("Olá! Conheci a Lambda Box e gostaria de conversar sobre um sistema para meu projeto.")
        return f"https://wa.me/{self.whatsapp}?text={message}" if self.whatsapp else ""

    @property
    def email_url(self) -> str:
        return f"mailto:{quote(self.email, safe='@.+-_')}" if self.email else ""

    @property
    def has_contact(self) -> bool:
        return bool(self.whatsapp or self.email or self.website or self.instagram or self.youtube)

    @property
    def pix_payload(self) -> str:
        try:
            return pix_payload(self.pix_key, self.pix_recipient_name, self.pix_recipient_city)
        except PixConfigurationError:
            return ""
