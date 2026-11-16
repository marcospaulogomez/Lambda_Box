"""Decode real PNG output and exercise the QR API without an Office engine."""

from io import BytesIO
import json
import unittest

from fastapi.testclient import TestClient
from PIL import Image
import zxingcpp

from suite.qr.generation import MAX_TEXT_BYTES, QrCodeError, generate_png
from suite.services.documents import ServiceError
from suite.services.qr_codes import QrCodeService
from suite.settings import Settings
from suite.web.application import create_app


def decode_png(png):
    with Image.open(BytesIO(png)) as image:
        code = zxingcpp.read_barcode(image)
        if code is None:
            raise AssertionError("Generated PNG could not be decoded")
        return code.bytes


class QrGenerationTests(unittest.TestCase):
    def test_png_round_trip_preserves_content_including_whitespace_and_unicode(self):
        for text in ["https://example.com/material?turma=1&dia=2", "  Ação e educação 🎉\nSegunda linha\t fim  ",
                     "日本語 e português", "x" * MAX_TEXT_BYTES, "á" * (MAX_TEXT_BYTES // 2)]:
            with self.subTest(length=len(text)):
                png = generate_png(text)
                self.assertEqual(decode_png(png), text.encode("utf-8"))
                with Image.open(BytesIO(png)) as image:
                    self.assertEqual(image.format, "PNG")
                    self.assertEqual(image.width, image.height)
                    # The quiet zone is white, even though the suite is dark.
                    self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))

    def test_optional_caption_is_outside_the_encoded_content(self):
        text = "https://example.com/aula"
        plain = generate_png(text)
        captioned = generate_png(text, "Material da aula — Educação")
        self.assertEqual(decode_png(captioned), text.encode())
        with Image.open(BytesIO(plain)) as source, Image.open(BytesIO(captioned)) as result:
            self.assertGreater(result.height, source.height)
            self.assertEqual(result.crop((0, 0, source.width, source.height)).tobytes(), source.tobytes())
            self.assertEqual(result.crop((0, source.height, result.width, result.height)).getextrema()[0][0], 0)

    def test_invalid_inputs_and_utf8_capacity_are_rejected(self):
        for text, caption in [("", ""), (" \n ", ""), (123, ""), ("x" * 1201, ""), ("á" * 601, ""),
                              ("\ud800", ""), ("ok", None), ("ok", "x" * 81), ("ok", "a\nb"),
                              ("ok", "\ud800"), ("ok", "a\x00b")]:
            with self.subTest(text_type=type(text), caption_type=type(caption)):
                with self.assertRaises(QrCodeError):
                    generate_png(text, caption)

    def test_service_bounds_concurrency_and_releases_slots_after_errors(self):
        service = QrCodeService()
        service.slots.acquire()
        service.slots.acquire()
        try:
            with self.assertRaises(ServiceError) as caught:
                service.generate("test")
            self.assertEqual(caught.exception.status_code, 429)
        finally:
            service.slots.release()
            service.slots.release()
        for _ in range(3):
            with self.assertRaises(ServiceError):
                service.generate("")
        self.assertEqual(decode_png(service.generate("after error")), b"after error")


class QrWebTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app(Settings(libreoffice_path="missing-engine-for-qr-test")))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def test_home_card_page_and_local_script_are_available(self):
        self.assertIn('href="/qr-code"', self.client.get("/").text)
        page = self.client.get("/qr-code")
        self.assertEqual(page.status_code, 200)
        self.assertIn('id="qr-form"', page.text)
        self.assertIn('id="qr-caption"', page.text)
        self.assertEqual(self.client.get("/static/qr-code.js").status_code, 200)

    def test_download_works_without_office_and_leaves_no_stored_jobs(self):
        self.assertFalse(self.client.get("/api/status").json()["conversion_available"])
        response = self.client.post("/api/qr-code", json={"text": "Olá 🌎", "caption": "Saudação"})
        self.assertEqual(response.status_code, 200, response.text if response.status_code != 200 else "")
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["content-disposition"], 'attachment; filename="qr-code.png"')
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(decode_png(response.content), "Olá 🌎".encode())
        self.assertEqual(list(self.client.app.state.documents.root.iterdir()), [])

    def test_invalid_json_fields_and_content_are_rejected(self):
        for data in [{}, [], None, {"text": None}, {"text": True}, {"text": "ok", "caption": 3},
                     {"text": "x" * 1201}, {"text": "ok", "extra": "unexpected"}, {"text": "\ud800"}]:
            with self.subTest(data_type=type(data)):
                # ASCII escaping also verifies escaped lone surrogates fail cleanly.
                response = self.client.post("/api/qr-code", content=json.dumps(data), headers={"Content-Type": "application/json"})
                self.assertEqual(response.status_code, 400, response.text)
                self.assertIsInstance(response.json()["detail"], str)
        for content in [b"{", b'{"text":"\xff"}', b'{"text":' + b"1" * 5000 + b"}", b"[" * 2000 + b"]" * 2000]:
            response = self.client.post("/api/qr-code", content=content, headers={"Content-Type": "application/json"})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post("/api/qr-code", content="plain text").status_code, 415)

    def test_body_limit_applies_before_parsing_including_streamed_requests(self):
        for content in [b"x" * 16385, iter([b'{"text":"', b"x" * 16385, b'"}'])]:
            response = self.client.post("/api/qr-code", content=content, headers={"Content-Type": "application/json"})
            self.assertEqual(response.status_code, 413)
        self.assertEqual(self.client.post("/api/qr-code", json={"text": "works afterwards"}).status_code, 200)

    def test_cross_origin_generation_is_rejected(self):
        response = self.client.post("/api/qr-code", json={"text": "test"}, headers={"Origin": "https://another.example"})
        self.assertEqual(response.status_code, 403)

    def test_openapi_documents_json_and_png(self):
        operation = self.client.get("/openapi.json").json()["paths"]["/api/qr-code"]["post"]
        self.assertIn("application/json", operation["requestBody"]["content"])
        self.assertIn("image/png", operation["responses"]["200"]["content"])
