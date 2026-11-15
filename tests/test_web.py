"""HTTP integration tests with real DOCX packages and a controlled PDF engine."""

from dataclasses import replace
import io
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zipfile

from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

from suite.conversion import BatchConversionResult, ConversionError
from suite.conversion.samples import generate_samples
from suite.settings import Settings
from suite.web.application import create_app
from test_pdf import pdf_bytes


class ControlledConverter:
    executable = Path(sys.executable)

    def __init__(self):
        self.calls = 0
        self.release = threading.Event()
        self.release.set()
        self.started = threading.Event()
        self.fail = False

    def convert_batch(self, sources, output_dir):
        self.calls += 1
        self.started.set()
        if not self.release.wait(5):
            raise ConversionError("Prazo de teste excedido.")
        if self.fail:
            raise ConversionError("O documento não pôde ser convertido.")
        output_dir.mkdir()
        outputs = []
        for index, _ in enumerate(sources, 1):
            writer = PdfWriter()
            for _ in range(index):
                writer.add_blank_page(width=595, height=842)
            path = output_dir / f"document-{index:03d}.pdf"
            writer.write(path)
            outputs.append(path)
        return BatchConversionResult(tuple(outputs), 0.01)


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.source = generate_samples(Path(self.temporary.name))[0].read_bytes()
        self.converter = ControlledConverter()
        self.settings = Settings()
        self.client = TestClient(create_app(self.settings, self.converter))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.addCleanup(self.converter.release.set)

    def send(self, files=None):
        return self.client.post("/api/jobs/word-to-pdf", files=files or [("files", ("relatorio.docx", self.source))])

    def finish(self, response):
        self.assertEqual(response.status_code, 202, response.text)
        job_id = response.json()["id"]
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            job = self.client.get(f"/api/jobs/{job_id}").json()
            if job["state"] in {"completed", "failed"}:
                return job
            threading.Event().wait(0.01)
        self.fail("Task did not finish")

    def test_home_and_tool_serve_without_external_assets(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn('href="/word-to-pdf"', home.text)
        self.assertEqual(home.text.count("EM BREVE"), 4)
        self.assertEqual(self.client.get("/word-to-pdf").status_code, 200)
        self.assertEqual(self.client.get("/static/word-to-pdf.js").status_code, 200)

    def test_single_document_download_delete_and_input_cleanup(self):
        job = self.finish(self.send())
        self.assertEqual(job["state"], "completed")
        self.assertEqual(job["files"][0]["name"], "001-relatorio.pdf")
        response = self.client.get(job["files"][0]["url"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(len(PdfReader(io.BytesIO(response.content)).pages), 1)
        root = self.client.app.state.documents.root
        self.assertFalse((root / job["id"] / "inputs").exists())
        self.assertEqual(self.client.get(f'/api/jobs/{job["id"]}/archive').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/jobs/{job["id"]}').status_code, 204)
        self.assertFalse((root / job["id"]).exists())
        self.assertEqual(self.client.get(job["files"][0]["url"]).status_code, 404)

    def test_batch_preserves_order_and_repeated_names_in_zip(self):
        job = self.finish(self.send([("files", ("C:\\fakepath\\ação.docx", self.source)),
                                     ("files", ("../../ação.docx", self.source))]))
        self.assertEqual(self.converter.calls, 1)
        self.assertEqual([file["name"] for file in job["files"]], ["001-ação.pdf", "002-ação.pdf"])
        archive_response = self.client.get(job["archive_url"])
        self.assertEqual(archive_response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(archive_response.content)) as archive:
            self.assertEqual(archive.namelist(), ["001-ação.pdf", "002-ação.pdf"])
            self.assertEqual([len(PdfReader(io.BytesIO(archive.read(name))).pages) for name in archive.namelist()], [1, 2])
        self.assertEqual(self.client.get(f'/api/jobs/{job["id"]}/files/0').status_code, 404)
        self.assertEqual(self.client.get(f'/api/jobs/{job["id"]}/files/3').status_code, 404)

    def test_invalid_uploads_do_not_launch_engine_or_leave_tasks(self):
        cases = [("wrong.pdf", self.source), ("empty.docx", b""), ("renamed.docx", b"not a docx")]
        for name, data in cases:
            with self.subTest(name=name):
                response = self.send([("files", (name, data))])
                self.assertEqual(response.status_code, 400, response.text)
                self.assertEqual(list(self.client.app.state.documents.root.iterdir()), [])
        self.assertEqual(self.converter.calls, 0)

    def test_failed_conversion_exposes_no_download_and_cleans_inputs(self):
        self.converter.fail = True
        job = self.finish(self.send())
        self.assertEqual(job["state"], "failed")
        self.assertIn("não pôde", job["error"])
        self.assertEqual(job["files"], [])
        self.assertEqual(self.client.get(f'/api/jobs/{job["id"]}/files/1').status_code, 409)
        self.assertFalse((self.client.app.state.documents.root / job["id"] / "inputs").exists())

    def test_queue_is_bounded_and_running_tasks_cannot_be_deleted(self):
        self.client.app.state.documents.settings = replace(self.settings, max_pending_jobs=1)
        self.converter.release.clear()
        first = self.send()
        self.assertTrue(self.converter.started.wait(1))
        self.assertEqual(self.send().status_code, 429)
        self.assertEqual(self.client.delete(f'/api/jobs/{first.json()["id"]}').status_code, 409)
        self.converter.release.set()
        self.assertEqual(self.finish(first)["state"], "completed")
        self.assertEqual(self.finish(self.send())["state"], "completed")

    def test_expiration_removes_artifacts_but_waits_for_active_download(self):
        job = self.finish(self.send())
        service = self.client.app.state.documents
        job_dir = service.root / job["id"]
        with service.download(job["id"], 1):
            with patch("suite.services.documents.time.time", return_value=job["expires_at"] + 1):
                service.cleanup()
                self.assertTrue(job_dir.exists())
                self.assertEqual(self.client.get(f'/api/jobs/{job["id"]}').status_code, 410)
        with patch("suite.services.documents.time.time", return_value=job["expires_at"] + 1):
            service.cleanup()
        self.assertFalse(job_dir.exists())
        self.assertEqual(self.client.get(f'/api/jobs/{job["id"]}').status_code, 404)

    def test_file_limits_are_checked_on_server(self):
        service = self.client.app.state.documents
        service.settings = replace(self.settings, max_file_bytes=len(self.source) - 1)
        self.assertEqual(self.send().status_code, 413)
        self.assertEqual(self.converter.calls, 0)
        self.assertEqual(list(service.root.iterdir()), [])
        too_many = [("files", (f"{index}.docx", self.source)) for index in range(11)]
        self.assertEqual(self.send(too_many).status_code, 400)

    def test_total_body_limit_including_chunked_requests(self):
        settings = replace(self.settings, max_total_bytes=1024)
        with TestClient(create_app(settings, self.converter)) as client:
            too_large = b"x" * (1024 * 1024 + 2048)
            response = client.post("/api/jobs/word-to-pdf", content=too_large)
            self.assertEqual(response.status_code, 413)
            chunks = iter([b'--b\r\nContent-Disposition: form-data; name="files"; filename="test.docx"\r\n\r\n', too_large, b'\r\n--b--\r\n'])
            response = client.post("/api/jobs/word-to-pdf", content=chunks, headers={"Content-Type": "multipart/form-data; boundary=b"})
            self.assertEqual(response.status_code, 413)
            self.assertEqual(self.converter.calls, 0)

    def test_missing_engine_returns_actionable_error(self):
        self.converter.executable = None
        self.assertFalse(self.client.get("/api/status").json()["conversion_available"])
        self.assertEqual(self.send().status_code, 503)

    def test_local_application_rejects_cross_origin_writes_and_unknown_hosts(self):
        response = self.client.post("/api/jobs/word-to-pdf", files=[("files", ("test.docx", self.source))],
                                    headers={"Origin": "https://another.example"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get("/", headers={"Host": "another.example"}).status_code, 400)
        response = self.client.post("/api/jobs/word-to-pdf", files=[("files", ("test.docx", self.source))],
                                    headers={"Origin": "http://testserver"})
        self.assertEqual(self.finish(response)["state"], "completed")

    def test_pdf_merge_works_without_libreoffice_and_uses_received_order(self):
        self.converter.executable = None
        sources = [("files", ("same.pdf", pdf_bytes(((842, 595),), rotation=90))),
                   ("files", ("same.pdf", pdf_bytes(((100, 200), (200, 300)))))]
        job = self.finish(self.client.post("/api/jobs/merge-pdfs", files=sources))
        self.assertEqual(job["state"], "completed")
        self.assertEqual(job["pages"], 3)
        self.assertEqual(job["operation"], "merge-pdfs")
        self.assertEqual(job["files"][0]["name"], "merged.pdf")
        reader = PdfReader(io.BytesIO(self.client.get(job["files"][0]["url"]).content))
        self.assertEqual([float(page.mediabox.width) for page in reader.pages], [842, 100, 200])
        self.assertEqual(reader.pages[0].rotation, 90)
        self.assertEqual(self.converter.calls, 0)
        self.assertIsNone(job["archive_url"])

    def test_combined_flow_keeps_interleaved_pdfs_and_converted_documents(self):
        sources = [("files", ("existing.pdf", pdf_bytes(((100, 200),)))),
                   ("files", ("report.docx", self.source)),
                   ("files", ("existing.pdf", pdf_bytes(((200, 300),)))),
                   ("files", ("report.docx", self.source))]
        job = self.finish(self.client.post("/api/jobs/convert-and-merge", files=sources))
        self.assertEqual(job["state"], "completed", job)
        reader = PdfReader(io.BytesIO(self.client.get(job["files"][0]["url"]).content))
        self.assertEqual([float(page.mediabox.width) for page in reader.pages], [100, 595, 200, 595, 595])
        self.assertEqual(self.converter.calls, 1)
        self.assertEqual(job["pages"], 5)
        directory = self.client.app.state.documents.root / job["id"]
        self.assertFalse((directory / "converted").exists())
        self.assertFalse((directory / "inputs").exists())

    def test_pdf_endpoints_reject_invalid_uploads_before_queueing(self):
        for files in [[("files", ("single.pdf", pdf_bytes()))],
                      [("files", ("one.pdf", pdf_bytes())), ("files", ("two.docx", self.source))],
                      [("files", ("one.pdf", pdf_bytes())), ("files", ("two.pdf", b"not pdf"))],
                      [("files", ("one.pdf", pdf_bytes())), ("files", ("two.pdf", pdf_bytes(password="secret")))]]:
            with self.subTest(files=[item[1][0] for item in files]):
                response = self.client.post("/api/jobs/merge-pdfs", files=files)
                self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(self.converter.calls, 0)
        self.assertEqual(list(self.client.app.state.documents.root.iterdir()), [])

    def test_combined_page_limit_applies_after_word_conversion(self):
        service = self.client.app.state.documents
        service.settings = replace(self.settings, max_pdf_pages=1)
        sources = [("files", ("one.pdf", pdf_bytes())), ("files", ("two.docx", self.source))]
        job = self.finish(self.client.post("/api/jobs/convert-and-merge", files=sources))
        self.assertEqual(job["state"], "failed")
        self.assertEqual(job["files"], [])
        self.assertIn("limite", job["error"])
        self.assertFalse((service.root / job["id"] / "converted").exists())

    def test_combined_pdf_only_job_does_not_require_word_engine(self):
        self.converter.executable = None
        sources = [("files", ("one.pdf", pdf_bytes())), ("files", ("two.pdf", pdf_bytes()))]
        job = self.finish(self.client.post("/api/jobs/convert-and-merge", files=sources))
        self.assertEqual(job["state"], "completed")
        sources[1] = ("files", ("two.docx", self.source))
        self.assertEqual(self.client.post("/api/jobs/convert-and-merge", files=sources).status_code, 503)

    def test_openapi_documents_multipart_uploads_for_all_tools(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        for operation in ("word-to-pdf", "merge-pdfs", "convert-and-merge"):
            schema = paths[f"/api/jobs/{operation}"]["post"]["requestBody"]["content"]["multipart/form-data"]["schema"]
            self.assertEqual(schema["properties"]["files"]["items"]["format"], "binary")


if __name__ == "__main__":
    unittest.main()
