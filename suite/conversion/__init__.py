"""Adaptadores de conversão, independentes da interface HTTP."""

from .libreoffice import ConversionError, ConversionResult, LibreOfficeConverter, find_libreoffice

__all__ = ["ConversionError", "ConversionResult", "LibreOfficeConverter", "find_libreoffice"]
