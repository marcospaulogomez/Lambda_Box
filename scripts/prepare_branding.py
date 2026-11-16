"""Wrap original PNG logos in SVG viewports, preserving their pixel data."""

import base64
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def svg_wrapper(source: Path, target: Path, *, square: bool = False):
    with Image.open(source) as image:
        width, height = image.size
        bounds = image.getchannel("A").getbbox() if image.mode == "RGBA" else (0, 0, width, height)
    if bounds is None:
        raise ValueError(f"Empty logo: {source.name}")
    left, top, right, bottom = bounds
    visible_width, visible_height = right - left, bottom - top
    padding = 4
    if square:
        size = max(visible_width, visible_height) + padding * 2
        left -= (size - visible_width) / 2
        top -= (size - visible_height) / 2
        visible_width = visible_height = size
    else:
        left -= padding
        top -= padding
        visible_width += padding * 2
        visible_height += padding * 2
    data = base64.b64encode(source.read_bytes()).decode("ascii")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{left:g} {top:g} {visible_width:g} {visible_height:g}" '
        f'width="{visible_width:g}" height="{visible_height:g}">\n'
        f'  <image width="{width}" height="{height}" href="data:image/png;base64,{data}"/>\n</svg>\n', encoding="utf-8")
    print(f"Prepared {target.relative_to(ROOT)}")


if __name__ == "__main__":
    sources = ROOT / "assets/branding"
    targets = ROOT / "suite/web/static/branding"
    svg_wrapper(sources / "lambda-box.png", targets / "lambda-box-logo.svg")
    svg_wrapper(sources / "lambda-technology.png", targets / "lambda-technology-logo.svg")
    svg_wrapper(sources / "lambda-box-symbol.png", targets / "favicon.svg", square=True)
