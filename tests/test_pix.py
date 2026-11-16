"""Verify the official BR Code example and decode donation QR output."""

from io import BytesIO
import unittest

from fastapi.testclient import TestClient
from PIL import Image
import zxingcpp

from suite.payments.pix import PixConfigurationError, pix_payload
from suite.site import SiteSettings
from suite.settings import Settings
from suite.web.application import create_app


class PixTests(unittest.TestCase):
    def test_matches_banco_central_static_example_and_crc(self):
        # Banco Central, Manual de Padrões para Iniciação do Pix, §2.6.3.
        expected = ("00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-426655440000"
                    "5204000053039865802BR5913Fulano de Tal6008BRASILIA62070503***63041D3D")
        self.assertEqual(pix_payload("123e4567-e12b-12d1-a456-426655440000", "Fulano de Tal", "BRASILIA"), expected)

    def test_normalizes_merchant_fields_and_leaves_amount_for_the_donor(self):
        payload = pix_payload("donation@example.com", "João de Exemplo " * 4, "Goiânia")
        fields = {}
        offset = 0
        while offset < len(payload):
            identifier, length = payload[offset:offset + 2], int(payload[offset + 2:offset + 4])
            fields[identifier] = payload[offset + 4:offset + 4 + length]
            offset += 4 + length
        self.assertEqual(offset, len(payload))
        self.assertNotIn("54", fields)
        self.assertEqual(fields["53"], "986")
        self.assertEqual(fields["60"], "Goiania")
        self.assertLessEqual(len(fields["59"]), 25)
        self.assertIn("donation@example.com", fields["26"])
        self.assertEqual(fields["62"], "0503***")

    def test_invalid_or_missing_payment_data_does_not_generate_a_code(self):
        for key, name, city in [("", "Example", "City"), ("invalid", "Example", "City"),
                                ("a" * 70 + "@example.com", "Example", "City"),
                                ("donation@example.com", "", "City"), ("donation@example.com", "Example", "")]:
            with self.subTest(key_length=len(key)):
                with self.assertRaises(PixConfigurationError):
                    pix_payload(key, name, city)

    def test_donation_image_decodes_to_the_same_copy_and_paste_payload(self):
        settings = SiteSettings(pix_key="donation@example.com", pix_recipient_name="Example Person", pix_recipient_city="Example City")
        with TestClient(create_app(Settings(libreoffice_path="missing-engine-for-pix-test"), site_settings=settings)) as client:
            page = client.get("/support")
            self.assertEqual(page.status_code, 200)
            self.assertIn('src="/support/pix.png"', page.text)
            self.assertIn(settings.pix_payload, page.text)
            self.assertIn('data-copy-target="pix-payload"', page.text)
            response = client.get("/support/pix.png")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"], "image/png")
            self.assertEqual(response.headers["cache-control"], "no-store")
            with Image.open(BytesIO(response.content)) as image:
                decoded = zxingcpp.read_barcode(image)
                self.assertIsNotNone(decoded)
                self.assertEqual(decoded.bytes, settings.pix_payload.encode("ascii"))
            self.assertEqual(list(client.app.state.documents.root.iterdir()), [])
