"""Exercise a running local suite with generated documents and the real engine."""

import argparse
from contextlib import ExitStack
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import uuid
import zipfile

import httpx
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from suite.conversion.samples import generate_samples


def main() -> None:
    parser = argparse.ArgumentParser(description="Verificar upload, lote, PDFs, ZIP e exclusão com o servidor local em execução.")
    parser.add_argument("--url", default="http://127.0.0.1:8090")
    args = parser.parse_args()
    run_dir = ROOT / "laboratorio" / "fluxo-web" / uuid.uuid4().hex[:8]
    sources = generate_samples(run_dir / "inputs")
    original_hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in sources]
    started = time.perf_counter()
    with httpx.Client(base_url=args.url, timeout=20, trust_env=False) as client:
        with ExitStack() as stack:
            uploads = [("files", (path.name, stack.enter_context(path.open("rb")), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")) for path in sources]
            response = client.post("/api/jobs/word-to-pdf", files=uploads)
        response.raise_for_status()
        job_id = response.json()["id"]
        deadline = time.monotonic() + 240
        while True:
            response = client.get(f"/api/jobs/{job_id}")
            response.raise_for_status()
            job = response.json()
            if job["state"] == "failed":
                raise RuntimeError(job["error"])
            if job["state"] == "completed":
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("Prazo de verificação excedido.")
            time.sleep(1)
        conversion_wall_seconds = round(time.perf_counter() - started, 3)
        contents = []
        pages = []
        for item in job["files"]:
            response = client.get(item["url"])
            response.raise_for_status()
            contents.append(response.content)
            pages.append(len(PdfReader(io.BytesIO(response.content)).pages))
            (run_dir / item["name"]).write_bytes(response.content)
        if pages != [1, 1, 1, 1, 2]:
            raise AssertionError(f"Paginação inesperada: {pages}")
        response = client.get(job["archive_url"])
        response.raise_for_status()
        (run_dir / "documents.zip").write_bytes(response.content)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            names = [item["name"] for item in job["files"]]
            if archive.namelist() != names or [archive.read(name) for name in names] != contents:
                raise AssertionError("O ZIP não corresponde aos downloads individuais.")
        client.delete(f"/api/jobs/{job_id}").raise_for_status()
        if client.get(job["files"][0]["url"]).status_code != 404:
            raise AssertionError("O download continuou disponível após a exclusão.")
    if original_hashes != [hashlib.sha256(path.read_bytes()).hexdigest() for path in sources]:
        raise AssertionError("Os documentos originais foram modificados.")
    report = {"created_at": datetime.now().astimezone().isoformat(), "files": len(sources), "pages": pages,
              "engine_seconds": job["seconds"], "upload_queue_conversion_seconds": conversion_wall_seconds,
              "individual_downloads": "passed", "zip_matches_downloads": "passed", "delete": "passed",
              "originals_unchanged": "passed", "visual_review": "pending"}
    (run_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    print(run_dir)


if __name__ == "__main__":
    main()
