"""Adaptadores de conversão, independentes da interface HTTP."""

from .libreoffice import BatchConversionResult, ConversionError, ConversionResult, LibreOfficeConverter, find_libreoffice, validate_docx

__all__ = ["BatchConversionResult", "ConversionError", "ConversionResult", "LibreOfficeConverter", "find_libreoffice", "validate_docx"]
