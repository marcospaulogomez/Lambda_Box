"""Check images-to-PDF through a running local HTTP server using generated fixtures."""

import argparse
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import time
import uuid

import httpx
from PIL import Image, ImageDraw
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Verificar imagens para PDF sem depender do LibreOffice.")
    parser.add_argument("--url", default="http://127.0.0.1:8090")
    args = parser.parse_args()
    run_dir = ROOT / "laboratory" / "image-flow" / uuid.uuid4().hex[:8]
    inputs = run_dir / "inputs"
    inputs.mkdir(parents=True)
    with Image.new("L", (120, 240), 80) as image:
        image.save(inputs / "portrait.png")
    with Image.new("RGB", (120, 60), "red") as image:
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 30, 30), fill="blue")
        exif = Image.Exif()
        exif[274] = 6
        image.save(inputs / "camera.jpg", exif=exif, quality=95)
    with Image.new("RGBA", (240, 120), (0, 255, 0, 0)) as image:
        draw = ImageDraw.Draw(image)
        draw.rectangle((60, 30, 180, 90), fill=(255, 0, 0, 255))
        image.save(inputs / "transparent.png")
    sources = [inputs / name for name in ("portrait.png", "camera.jpg", "transparent.png")]
    originals = [hashlib.sha256(path.read_bytes()).hexdigest() for path in sources]
    with httpx.Client(base_url=args.url, timeout=20, trust_env=False) as client:
        started = time.perf_counter()
        response = client.post("/api/jobs/images-to-pdf", files=[("files", (path.name, path.read_bytes())) for path in sources])
        response.raise_for_status()
        job_id = response.json()["id"]
        deadline = time.monotonic() + 60
        while True:
            response = client.get(f"/api/jobs/{job_id}")
            response.raise_for_status()
            job = response.json()
            if job["state"] == "failed":
                raise RuntimeError(job["error"])
            if job["state"] == "completed":
                break
            if time.monotonic() > deadline:
                raise RuntimeError("Prazo de verificação excedido.")
            time.sleep(.2)
        elapsed = round(time.perf_counter() - started, 3)
        url = job["files"][0]["url"]
        response = client.get(url)
        response.raise_for_status()
        (run_dir / "images.pdf").write_bytes(response.content)
        reader = PdfReader(io.BytesIO(response.content))
        if len(reader.pages) != 3 or job["pages"] != 3:
            raise AssertionError("Quantidade de páginas incorreta.")
        images = [page.images[0].image for page in reader.pages]
        if [image.size for image in images] != [(120, 240), (60, 120), (240, 120)]:
            raise AssertionError("Ordem, resolução ou orientação EXIF incorreta.")
        if [page.mediabox.width > page.mediabox.height for page in reader.pages] != [False, False, True]:
            raise AssertionError("Orientação das páginas incorreta.")
        if images[0].getpixel((0, 0)) != (80, 80, 80) or images[2].getpixel((0, 0)) != (255, 255, 255):
            raise AssertionError("Cinza ou transparência incorretos.")
        if images[2].getpixel((120, 60)) != (255, 0, 0):
            raise AssertionError("Conteúdo da imagem alterado.")
        client.delete(f"/api/jobs/{job_id}").raise_for_status()
        if client.get(url).status_code != 404:
            raise AssertionError("O PDF continuou disponível após a exclusão.")
        invalid = client.post("/api/jobs/images-to-pdf", files=[("files", ("broken.png", b"not an image"))])
        if invalid.status_code != 400:
            raise AssertionError("Arquivo inválido não foi rejeitado.")
    if originals != [hashlib.sha256(path.read_bytes()).hexdigest() for path in sources]:
        raise AssertionError("Os originais foram modificados.")
    report = {"created_at": datetime.now().astimezone().isoformat(), "files": 3, "pages": 3,
              "processing_seconds": job["seconds"], "upload_queue_processing_seconds": elapsed,
              "order_exif_dimensions": "passed", "transparency": "passed", "delete": "passed",
              "invalid_upload": "passed", "originals_unchanged": "passed", "visual_review": "pending"}
    (run_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    print(run_dir)


if __name__ == "__main__":
    main()
