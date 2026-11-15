"""Validate image content and inspect the actual geometry and pixels in the PDF."""

import io
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from pypdf import PdfReader
from reportlab.lib.units import mm

from suite.images import ImageProcessingError, images_to_pdf, validate_image


def image_bytes(size=(40, 20), *, color="red", mode="RGB", format="PNG", orientation=None):
    stream = io.BytesIO()
    with Image.new(mode, size, color) as image:
        options = {}
        if orientation:
            exif = Image.Exif()
            exif[274] = orientation
            options["exif"] = exif
        image.save(stream, format, **options)
    return stream.getvalue()


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def source(self, name, data):
        path = self.root / name
        path.write_bytes(data)
        return path

    def test_order_page_orientation_proportion_margins_and_unchanged_originals(self):
        first = self.source("portrait.png", image_bytes((20, 40), color="blue"))
        second = self.source("landscape.jpg", image_bytes((40, 20), format="JPEG"))
        originals = [path.read_bytes() for path in (first, second)]
        result = images_to_pdf([first, second], self.root / "images.pdf")
        reader = PdfReader(result.output)
        self.assertEqual(result.pages, 2)
        self.assertLess(reader.pages[0].mediabox.width, reader.pages[0].mediabox.height)
        self.assertGreater(reader.pages[1].mediabox.width, reader.pages[1].mediabox.height)
        for page, size in zip(reader.pages, [(20, 40), (40, 20)]):
            embedded = page.images[0].image
            self.assertEqual(embedded.size, size)
            matrix = None
            for operands, operator in page.get_contents().operations:
                if operator == b"cm":
                    matrix = [float(value) for value in operands]
                if operator == b"Do":
                    width, _, _, height, x, y = matrix
                    self.assertAlmostEqual(width / height, size[0] / size[1], places=5)
                    self.assertGreaterEqual(x + .001, 12 * mm)
                    self.assertGreaterEqual(y + .001, 12 * mm)
                    self.assertLessEqual(x + width, float(page.mediabox.width) - 12 * mm + .001)
                    self.assertLessEqual(y + height, float(page.mediabox.height) - 12 * mm + .001)
                    self.assertAlmostEqual(x, (float(page.mediabox.width) - width) / 2, places=3)
                    self.assertAlmostEqual(y, (float(page.mediabox.height) - height) / 2, places=3)
        self.assertEqual(reader.pages[0].images[0].image.getpixel((0, 0)), (0, 0, 255))
        self.assertEqual([path.read_bytes() for path in (first, second)], originals)

    def test_exif_rotation_is_applied_before_page_orientation(self):
        source = self.source("camera.jpeg", image_bytes((40, 20), format="JPEG", orientation=6))
        result = images_to_pdf([source], self.root / "images.pdf")
        page = PdfReader(result.output).pages[0]
        self.assertEqual(page.images[0].image.size, (20, 40))
        self.assertLess(page.mediabox.width, page.mediabox.height)
        # An asymmetric lossless fixture checks the actual direction of rotation.
        with Image.new("RGB", (4, 2), "white") as image:
            image.putpixel((0, 0), (255, 0, 0))
            image.putpixel((3, 1), (0, 0, 255))
            exif = Image.Exif()
            exif[274] = 6
            image.save(self.root / "direction.png", exif=exif)
        result = images_to_pdf([self.root / "direction.png"], self.root / "direction.pdf")
        image = PdfReader(result.output).pages[0].images[0].image
        self.assertEqual(image.getpixel((1, 0)), (255, 0, 0))
        self.assertEqual(image.getpixel((0, 3)), (0, 0, 255))

    def test_alpha_and_palette_transparency_are_composited_on_white(self):
        with Image.new("RGBA", (4, 2), (0, 255, 0, 0)) as image:
            image.putpixel((0, 0), (255, 0, 0, 255))
            image.putpixel((1, 0), (0, 0, 255, 128))
            image.save(self.root / "alpha.png")
        with Image.new("P", (2, 2), 0) as image:
            image.putpalette([0, 255, 0, 255, 0, 0] + [0] * 762)
            image.putpixel((0, 0), 1)
            image.save(self.root / "palette.png", transparency=0)
        result = images_to_pdf([self.root / "alpha.png", self.root / "palette.png"], self.root / "images.pdf")
        pages = PdfReader(result.output).pages
        first, second = [page.images[0].image for page in pages]
        self.assertEqual(first.getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(first.getpixel((1, 0)), (127, 127, 255))
        self.assertEqual(first.getpixel((2, 1)), (255, 255, 255))
        self.assertEqual(second.getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(second.getpixel((1, 1)), (255, 255, 255))

    def test_grayscale_and_cmyk_inputs_generate_rgb_pages(self):
        first = self.source("gray.png", image_bytes(mode="L", color=80))
        second = self.source("cmyk.jpg", image_bytes(mode="CMYK", color=(0, 255, 255, 0), format="JPEG"))
        result = images_to_pdf([first, second], self.root / "images.pdf")
        images = [page.images[0].image for page in PdfReader(result.output).pages]
        self.assertEqual(images[0].getpixel((0, 0)), (80, 80, 80))
        self.assertEqual(images[1].mode, "RGB")

    def test_rejects_mismatched_corrupt_animated_and_high_depth_inputs(self):
        cases = [("renamed.png", image_bytes(format="JPEG")), ("broken.jpg", b"not an image"),
                 ("truncated.png", image_bytes()[:50]), ("high-depth.png", image_bytes(mode="I;16", color=1000))]
        with Image.new("RGB", (2, 2), "red") as first, Image.new("RGB", (2, 2), "blue") as second:
            first.save(self.root / "animated.png", save_all=True, append_images=[second], duration=100, loop=0)
        cases.append(("animated.png", (self.root / "animated.png").read_bytes()))
        for name, data in cases:
            with self.subTest(name=name):
                with self.assertRaises(ImageProcessingError):
                    validate_image(self.source(name, data))

    def test_pixel_budgets_page_limit_and_failure_leave_no_partial_result(self):
        first = self.source("one.png", image_bytes())
        second = self.source("two.png", image_bytes())
        output = self.root / "images.pdf"
        for limits in ({"max_pixels": 799}, {"max_total_pixels": 1599}, {"max_pages": 1}):
            with self.subTest(limits=limits):
                with self.assertRaises(ImageProcessingError):
                    images_to_pdf([first, second], output, **limits)
                self.assertFalse(output.exists())
        second.write_bytes(b"broken")
        with self.assertRaisesRegex(ImageProcessingError, "Imagem 2"):
            images_to_pdf([first, second], output)
        self.assertFalse(output.exists())

    def test_existing_result_is_preserved(self):
        source = self.source("image.png", image_bytes())
        output = self.source("images.pdf", b"user result")
        with self.assertRaisesRegex(ImageProcessingError, "Já existe"):
            images_to_pdf([source], output)
        self.assertEqual(output.read_bytes(), b"user result")
