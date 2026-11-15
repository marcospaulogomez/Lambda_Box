"""Check page order, geometry, protection and publication with real PDF files."""

import io
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader, PdfWriter

from suite.pdf import PdfProcessingError, merge_pdfs, validate_pdf


def pdf_bytes(dimensions=((595, 842),), *, rotation=0, password=None):
    writer = PdfWriter()
    for width, height in dimensions:
        page = writer.add_blank_page(width=width, height=height)
        if rotation:
            page.rotate(rotation)
    if password:
        writer.encrypt(password)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


class PdfTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def source(self, name, data):
        path = self.root / name
        path.write_bytes(data)
        return path

    def test_merge_preserves_order_dimensions_rotation_and_originals(self):
        first = self.source("first.pdf", pdf_bytes(((100, 200), (200, 300))))
        second = self.source("second.pdf", pdf_bytes(((842, 595),), rotation=90))
        originals = [path.read_bytes() for path in (first, second)]
        result = merge_pdfs([second, first], self.root / "merged.pdf")
        reader = PdfReader(result.output)
        self.assertEqual(result.pages, 3)
        self.assertEqual([(float(page.mediabox.width), float(page.mediabox.height), page.rotation) for page in reader.pages],
                         [(842, 595, 90), (100, 200, 0), (200, 300, 0)])
        self.assertEqual([path.read_bytes() for path in (first, second)], originals)

    def test_rejects_corrupt_protected_and_empty_documents(self):
        for name, data in [("corrupt.pdf", b"%PDF-1.7\ntruncated"), ("protected.pdf", pdf_bytes(password="secret")),
                           ("empty.pdf", pdf_bytes(())), ("renamed.pdf", b"html")]:
            with self.subTest(name=name):
                source = self.source(name, data)
                with self.assertRaises(PdfProcessingError):
                    validate_pdf(source)

    def test_page_limit_and_invalid_second_input_leave_no_result(self):
        first = self.source("first.pdf", pdf_bytes(((100, 200), (200, 300))))
        second = self.source("second.pdf", pdf_bytes())
        output = self.root / "merged.pdf"
        with self.assertRaisesRegex(PdfProcessingError, "limite"):
            merge_pdfs([first, second], output, max_pages=2)
        self.assertFalse(output.exists())
        second.write_bytes(b"broken")
        with self.assertRaisesRegex(PdfProcessingError, "Documento 2"):
            merge_pdfs([first, second], output)
        self.assertFalse(output.exists())

    def test_existing_output_is_preserved(self):
        source = self.source("source.pdf", pdf_bytes())
        output = self.source("merged.pdf", b"user result")
        with self.assertRaisesRegex(PdfProcessingError, "Já existe"):
            merge_pdfs([source], output)
        self.assertEqual(output.read_bytes(), b"user result")
