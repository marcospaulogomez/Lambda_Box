from pathlib import Path
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

from suite.conversion import ConversionError, LibreOfficeConverter, find_libreoffice
from suite.conversion.samples import generate_samples
from suite.conversion.libreoffice import _execute
from validar_conversao import inspect_pdf, main, write_report


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.documents = generate_samples(self.root / "entrada")
        self.converter = LibreOfficeConverter(sys.executable)

    def test_invalid_docx_is_rejected_before_launch(self):
        invalid = self.root / "invalido.docx"
        invalid.write_text("Isto não é um DOCX", encoding="utf-8")
        with patch("suite.conversion.libreoffice._execute") as execute:
            with self.assertRaisesRegex(ConversionError, "inválido"):
                self.converter.convert(invalid, self.root / "saida")
            execute.assert_not_called()

    def test_zero_exit_without_pdf_is_failure(self):
        with patch("suite.conversion.libreoffice._execute", return_value=subprocess.CompletedProcess([], 0, "", "")):
            with self.assertRaisesRegex(ConversionError, "sem gerar"):
                self.converter.convert(self.documents[0], self.root / "saida")

    def test_nonzero_exit_does_not_publish_output(self):
        with patch("suite.conversion.libreoffice._execute", return_value=subprocess.CompletedProcess([], 1, "", "Falha de leitura")):
            with self.assertRaisesRegex(ConversionError, "Falha de leitura"):
                self.converter.convert(self.documents[0], self.root / "saida")
        self.assertFalse((self.root / "saida").exists())

    def test_version_failure_without_output_includes_exit_code(self):
        with patch("suite.conversion.libreoffice._execute", return_value=subprocess.CompletedProcess([], 7, "", "")):
            with self.assertRaisesRegex(ConversionError, "código de saída 7"):
                self.converter.version()

    def test_html_renamed_to_pdf_is_not_published(self):
        def fake_engine(command, timeout):
            (Path(command[command.index("--outdir") + 1]) / "entrada.pdf").write_bytes(b"<html>erro</html>")
            return subprocess.CompletedProcess(command, 0, "", "")
        with patch("suite.conversion.libreoffice._execute", side_effect=fake_engine):
            with self.assertRaisesRegex(ConversionError, "cabeçalho PDF"):
                self.converter.convert(self.documents[0], self.root / "saida")
        self.assertFalse((self.root / "saida").exists())

    def test_existing_result_is_not_overwritten(self):
        output = self.root / "saida"
        output.mkdir()
        result = output / f"{self.documents[0].stem}.pdf"
        result.write_bytes(b"resultado do usuario")
        with patch("suite.conversion.libreoffice._execute") as execute:
            with self.assertRaisesRegex(ConversionError, "Já existe"):
                self.converter.convert(self.documents[0], output)
            execute.assert_not_called()
        self.assertEqual(result.read_bytes(), b"resultado do usuario")

    def test_runs_use_different_profiles_and_leave_original_unchanged(self):
        profiles = []
        original = self.documents[0].read_bytes()
        def fake_engine(command, timeout):
            profiles.append(next(value for value in command if value.startswith("-env:UserInstallation=")))
            (Path(command[command.index("--outdir") + 1]) / "entrada.pdf").write_bytes(b"%PDF-1.7\nresultado ficticio de contrato")
            return subprocess.CompletedProcess(command, 0, "", "")
        with patch("suite.conversion.libreoffice._execute", side_effect=fake_engine):
            first = self.converter.convert(self.documents[0], self.root / "primeiro")
            second = self.converter.convert(self.documents[0], self.root / "segundo")
        self.assertNotEqual(profiles[0], profiles[1])
        self.assertEqual(first.output.read_bytes(), second.output.read_bytes())
        self.assertEqual(self.documents[0].read_bytes(), original)

    def test_batch_launches_once_with_safe_names_and_separate_profiles(self):
        calls = []
        originals = [path.read_bytes() for path in self.documents[:2]]
        def fake_engine(command, timeout):
            calls.append(command)
            output = Path(command[command.index("--outdir") + 1])
            for source in (Path(value) for value in command if value.endswith(".docx")):
                (output / source.with_suffix(".pdf").name).write_bytes(b"%PDF-1.7\ncontract")
            return subprocess.CompletedProcess(command, 0, "", "")
        with patch("suite.conversion.libreoffice._execute", side_effect=fake_engine):
            first = self.converter.convert_batch(self.documents[:2], self.root / "batch-1")
            second = self.converter.convert_batch(self.documents[:2], self.root / "batch-2")
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(first.outputs), 2)
        self.assertEqual([path.name for path in first.outputs], ["document-001.pdf", "document-002.pdf"])
        profiles = [next(value for value in call if value.startswith("-env:UserInstallation=")) for call in calls]
        self.assertNotEqual(profiles[0], profiles[1])
        self.assertEqual([path.read_bytes() for path in self.documents[:2]], originals)
        self.assertEqual([path.read_bytes() for path in first.outputs], [path.read_bytes() for path in second.outputs])

    def test_batch_missing_pdf_does_not_publish_partial_results(self):
        def incomplete_engine(command, timeout):
            output = Path(command[command.index("--outdir") + 1])
            (output / "document-001.pdf").write_bytes(b"%PDF-1.7\ncontract")
            return subprocess.CompletedProcess(command, 0, "", "")
        with patch("suite.conversion.libreoffice._execute", side_effect=incomplete_engine):
            with self.assertRaisesRegex(ConversionError, "documento 2"):
                self.converter.convert_batch(self.documents[:2], self.root / "batch")
        self.assertFalse((self.root / "batch").exists())

    def test_batch_refuses_existing_output_before_engine_launch(self):
        output = self.root / "batch"
        output.mkdir()
        existing = output / "document-002.pdf"
        existing.write_bytes(b"user output")
        with patch("suite.conversion.libreoffice._execute") as execute:
            with self.assertRaisesRegex(ConversionError, "Já existe"):
                self.converter.convert_batch(self.documents[:2], output)
            execute.assert_not_called()
        self.assertEqual(existing.read_bytes(), b"user output")

    def test_explicit_missing_executable_does_not_fall_back(self):
        self.assertIsNone(find_libreoffice(self.root / "inexistente.exe"))

    def test_execution_timeout_stops_the_owned_process(self):
        with self.assertRaisesRegex(ConversionError, "excedeu o limite"):
            _execute([sys.executable, "-c", "import time; time.sleep(10)"], 0.1)

    def test_sample_generation_preserves_user_edits(self):
        self.documents[0].write_bytes(b"alteracao feita pelo usuario")
        generate_samples(self.documents[0].parent)
        self.assertEqual(self.documents[0].read_bytes(), b"alteracao feita pelo usuario")

    def test_samples_have_well_formed_xml_and_embedded_image(self):
        for document in self.documents:
            with self.subTest(document=document.name), zipfile.ZipFile(document) as package:
                self.assertIsNone(package.testzip())
                for name in package.namelist():
                    if name.endswith((".xml", ".rels")):
                        ET.fromstring(package.read(name))
        with zipfile.ZipFile(self.documents[2]) as package:
            self.assertTrue(package.read("word/media/padrao.png").startswith(b"\x89PNG\r\n\x1a\n"))

    def test_samples_define_line_and_paragraph_spacing(self):
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        word = '{' + ns['w'] + '}'
        with zipfile.ZipFile(self.documents[0]) as package:
            styles = ET.fromstring(package.read("word/styles.xml"))
            default = styles.find("w:docDefaults/w:pPrDefault/w:pPr/w:spacing", ns)
            self.assertEqual(default.attrib[word + "line"], "276")
            self.assertEqual(default.attrib[word + "lineRule"], "auto")
            self.assertEqual(default.attrib[word + "after"], "160")
            document = ET.fromstring(package.read("word/document.xml"))
            self.assertGreaterEqual(len(document.findall(".//w:br", ns)), 2)

    def test_sample_image_has_explicit_zero_distances_and_left_alignment(self):
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main", "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"}
        with zipfile.ZipFile(self.documents[2]) as package:
            document = ET.fromstring(package.read("word/document.xml"))
            image = document.find(".//wp:inline", ns)
            self.assertEqual([image.attrib[key] for key in ("distL", "distR", "distT", "distB")], ["0"] * 4)
            paragraph = next(p for p in document.findall(".//w:p", ns) if p.find(".//wp:inline", ns) is not None)
            self.assertEqual(paragraph.find("w:pPr/w:jc", ns).attrib['{' + ns['w'] + '}val'], "left")

    def test_cli_can_generate_revised_examples_in_another_folder(self):
        revised = self.root / "entrada-v2"
        original = self.documents[0].read_bytes()
        with patch("builtins.print"):
            result = main(["--gerar-exemplos", "--pasta-exemplos", str(revised)])
        self.assertEqual(result, 0)
        self.assertEqual(len(list(revised.glob("*.docx"))), 5)
        self.assertEqual(self.documents[0].read_bytes(), original)

    def test_empty_input_directory_returns_actionable_failure(self):
        with patch("builtins.print"):
            self.assertEqual(main(["--entrada", str(self.root)]), 2)

    def test_help_works_with_legacy_console_encoding(self):
        command = Path(__file__).resolve().parents[1] / "validar_conversao.py"
        result = subprocess.run(
            [sys.executable, str(command), "--help"], capture_output=True,
            env={**os.environ, "PYTHONIOENCODING": "cp1252"}, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        self.assertIn("--relatorio", result.stdout.decode("utf-8"))

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "pypdf opcional não instalado")
    def test_real_pdf_page_count_and_dimensions(self):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=842, height=595)
        writer.add_blank_page(width=595, height=842)
        path = self.root / "dimensoes.pdf"
        with path.open("wb") as stream:
            writer.write(stream)
        result = inspect_pdf(path)
        self.assertEqual(result["paginas"], 2)
        self.assertEqual(result["dimensoes_pt"], [[842.0, 595.0], [595.0, 842.0]])

    def test_report_escapes_document_names_and_marks_visual_review_pending(self):
        report = {"motor": "LibreOffice", "criado_em": "teste", "arquivos": [{"nome": "<script>alert(1)</script>", "entrada": str(self.documents[0]), "status": "falha", "erro": "<erro>"}]}
        output = write_report(self.root / "relatorio", report)
        content = output.read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", content)
        self.assertIn("&lt;script&gt;", content)
        self.assertIn("Avaliação visual pendente", content)


if __name__ == "__main__":
    unittest.main()
