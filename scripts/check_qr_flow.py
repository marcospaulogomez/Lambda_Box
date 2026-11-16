"""Exercise the running local QR tool and decode the downloaded PNG."""

import argparse
from io import BytesIO
from pathlib import Path
import sys

import httpx
from PIL import Image
import zxingcpp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8090")
    args = parser.parse_args()
    text = "https://example.com/aula?tema=educação&turma=1"
    with httpx.Client(base_url=args.url, trust_env=False, timeout=30) as client:
        home = client.get("/")
        home.raise_for_status()
        if 'href="/qr-code"' not in home.text:
            raise RuntimeError("O cartão de QR Code não está disponível. Reinicie a suíte.")
        client.get("/qr-code").raise_for_status()
        response = client.post("/api/qr-code", json={"text": text, "caption": "Material da aula"})
        response.raise_for_status()
        if response.headers.get("content-type") != "image/png":
            raise RuntimeError("O servidor não devolveu um PNG.")
        with Image.open(BytesIO(response.content)) as image:
            decoded = zxingcpp.read_barcode(image)
            if decoded is None or decoded.bytes != text.encode("utf-8"):
                raise RuntimeError("O QR Code não recuperou o texto original.")
        invalid = client.post("/api/qr-code", json={"text": "á" * 601})
        if invalid.status_code != 400:
            raise RuntimeError("O servidor não aplicou o limite de conteúdo.")
    output = Path(__file__).resolve().parents[1] / "laboratory" / "qr-flow" / "qr-code.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(response.content)
    print(f"QR Code gerado, baixado e decodificado com sucesso. Exemplo: {output}")


if __name__ == "__main__":
    try:
        main()
    except (httpx.HTTPError, RuntimeError) as exc:
        print(f"Falha na verificação: {exc}", file=sys.stderr)
        raise SystemExit(1)
