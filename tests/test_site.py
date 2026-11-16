"""Verify dotenv isolation and the public contact/donation experience."""

from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from suite.site import SiteSettings
from suite.settings import Settings
from suite.web.application import create_app


class SiteSettingsTests(unittest.TestCase):
    def test_loads_only_public_fields_without_mutating_the_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text('CONTACT_EMAIL=hello@example.com\nCONTACT_WHATSAPP="+55 (11) 99999-0000"\n'
                            'PIX_KEY="sample-key"\nPIX_RECIPIENT_NAME="Example Name"\n'
                            'PRIVATE_TOKEN=must-not-appear\nCONTACT_WEBSITE=https://example.com\n', encoding="utf-8")
            with patch.dict("os.environ", {}, clear=True):
                settings = SiteSettings.local(path)
                self.assertNotIn("CONTACT_EMAIL", os.environ)
            self.assertEqual(settings.email, "hello@example.com")
            self.assertEqual(settings.whatsapp, "5511999990000")
            self.assertTrue(settings.whatsapp_url.startswith("https://wa.me/5511999990000?text="))
            self.assertTrue(settings.has_contact)
            self.assertNotIn("PRIVATE_TOKEN", vars(settings))

    def test_environment_takes_precedence_and_empty_values_hide_channels(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("CONTACT_EMAIL=old@example.com\nPIX_KEY=old-key\n", encoding="utf-8")
            with patch.dict("os.environ", {"CONTACT_EMAIL": "new@example.com", "PIX_KEY": ""}, clear=True):
                settings = SiteSettings.local(path)
            self.assertEqual(settings.email, "new@example.com")
            self.assertEqual(settings.pix_key, "")

    def test_rejects_unsafe_links_invalid_contacts_and_control_characters(self):
        with patch.dict("os.environ", {"CONTACT_WEBSITE": "javascript:alert(1)",
                                       "CONTACT_INSTAGRAM": "https://user:pass@example.com",
                                       "DONATION_URL": "https://example.com\n/evil", "CONTACT_EMAIL": "bad@example.com?subject=bad",
                                       "CONTACT_WHATSAPP": "invalid5511999990000", "PIX_KEY": "bad\nkey"}, clear=True):
            settings = SiteSettings.local(Path(tempfile.gettempdir()) / "nonexistent-lambda-test.env")
        self.assertFalse(settings.has_contact)
        self.assertEqual(settings.donation_url, "")
        self.assertEqual(settings.pix_key, "")


class SiteWebTests(unittest.TestCase):
    def client(self, settings):
        client = TestClient(create_app(Settings(libreoffice_path="missing-engine-for-site-test"), site_settings=settings))
        client.__enter__()
        self.addCleanup(client.__exit__, None, None, None)
        return client

    def test_branding_navigation_and_empty_contact_states_work_on_every_tool(self):
        client = self.client(SiteSettings())
        for path in ["/", "/word-to-pdf", "/merge-pdfs", "/convert-and-merge", "/images-to-pdf", "/qr-code", "/contact", "/support"]:
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn("· Lambda Box</title>", response.text)
                self.assertIn('href="/contact"', response.text)
                self.assertIn('href="/support"', response.text)
                self.assertIn("branding/favicon.svg", response.text)
                self.assertNotIn('href="mailto:', response.text)
                self.assertNotIn('href="https://wa.me/', response.text)
        self.assertIn("Os canais de contato serão divulgados em breve", client.get("/contact").text)
        support = client.get("/support")
        self.assertIn("As formas de doação serão disponibilizadas em breve", support.text)
        self.assertNotIn('data-copy-target="pix-key"', support.text)
        self.assertEqual(client.get("/support/pix.png").status_code, 404)
        for asset in ["favicon.svg", "lambda-box-logo.svg", "lambda-technology-logo.svg"]:
            self.assertEqual(client.get(f"/static/branding/{asset}").status_code, 200)

    def test_public_contacts_and_pix_render_with_escaping(self):
        settings = SiteSettings(whatsapp="5511999990000", email="hello@example.com", website="https://example.com",
                                pix_key='test<&"key', pix_recipient_name="Example <Name>", pix_recipient_city="Example City",
                                donation_url="https://example.com/donate", repository_url="https://example.com/source")
        client = self.client(settings)
        contact = client.get("/contact")
        self.assertIn("https://wa.me/5511999990000", contact.text)
        self.assertIn('href="mailto:hello@example.com"', contact.text)
        support = client.get("/support")
        self.assertIn('data-copy-target="pix-key"', support.text)
        self.assertIn("test&lt;&amp;&#34;key", support.text)
        self.assertIn("Example &lt;Name&gt;", support.text)
        self.assertNotIn("Example <Name>", support.text)
        self.assertEqual(support.headers["cache-control"], "no-store")
        self.assertIn('href="https://example.com/donate"', support.text)
        self.assertIn('aria-current="page"', support.text)

    def test_environment_files_and_nonpublic_settings_are_never_served(self):
        client = self.client(SiteSettings())
        for path in ["/.env", "/.env.example", "/static/.env", "/static/../.env"]:
            self.assertEqual(client.get(path).status_code, 404, path)
        status = client.get("/api/status").json()
        self.assertNotIn("site", status)
        self.assertNotIn("pix_key", status)
        self.assertNotIn("email", status)
