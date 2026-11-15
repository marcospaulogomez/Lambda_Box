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
    parser.add_argument("--pdf-tools", action="store_true", help="Verifica também juntar PDFs e converter e juntar.")
    args = parser.parse_args()
    run_dir = ROOT / "laboratory" / "web-flow" / uuid.uuid4().hex[:8]
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
        pdf_tools = {}
        if args.pdf_tools:
            def signature(data):
                # PDF serialization rounds numeric objects; compare to 0.001 point.
                return [(round(float(page.mediabox.width), 3), round(float(page.mediabox.height), 3), page.rotation, page.extract_text())
                        for page in PdfReader(io.BytesIO(data)).pages]

            def check_tool(operation, uploads, expected):
                response = client.post(f"/api/jobs/{operation}", files=uploads)
                response.raise_for_status()
                tool_id = response.json()["id"]
                deadline = time.monotonic() + 240
                while True:
                    response = client.get(f"/api/jobs/{tool_id}")
                    response.raise_for_status()
                    tool_job = response.json()
                    if tool_job["state"] == "failed":
                        raise RuntimeError(tool_job["error"])
                    if tool_job["state"] == "completed":
                        break
                    if time.monotonic() > deadline:
                        raise RuntimeError("Prazo de verificação excedido.")
                    time.sleep(1)
                response = client.get(tool_job["files"][0]["url"])
                response.raise_for_status()
                if signature(response.content) != expected:
                    raise AssertionError(f"Ordem, texto ou dimensões incorretos em {operation}.")
                (run_dir / f"{operation}.pdf").write_bytes(response.content)
                client.delete(f"/api/jobs/{tool_id}").raise_for_status()
                if client.get(tool_job["files"][0]["url"]).status_code != 404:
                    raise AssertionError("O resultado permaneceu disponível após a exclusão.")
                pdf_tools[operation] = {"status": "passed", "pages": tool_job["pages"], "seconds": tool_job["seconds"]}

            check_tool("merge-pdfs", [("files", ("same.pdf", contents[4])), ("files", ("same.pdf", contents[3]))],
                       signature(contents[4]) + signature(contents[3]))
            check_tool("convert-and-merge", [("files", ("before.pdf", contents[3])), ("files", (sources[0].name, sources[0].read_bytes())),
                                              ("files", ("after.pdf", contents[4]))],
                       signature(contents[3]) + signature(contents[0]) + signature(contents[4]))
        client.delete(f"/api/jobs/{job_id}").raise_for_status()
        if client.get(job["files"][0]["url"]).status_code != 404:
            raise AssertionError("O download continuou disponível após a exclusão.")
    if original_hashes != [hashlib.sha256(path.read_bytes()).hexdigest() for path in sources]:
        raise AssertionError("Os documentos originais foram modificados.")
    report = {"created_at": datetime.now().astimezone().isoformat(), "files": len(sources), "pages": pages,
              "engine_seconds": job["seconds"], "upload_queue_conversion_seconds": conversion_wall_seconds,
              "individual_downloads": "passed", "zip_matches_downloads": "passed", "delete": "passed",
              "originals_unchanged": "passed", "visual_review": "pending", "pdf_tools": pdf_tools}
    (run_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    print(run_dir)


if __name__ == "__main__":
    main()
