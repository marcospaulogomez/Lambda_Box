"""Launch the modular suite locally while keeping the original converter available."""

import argparse
import socket
import sys
import threading
import webbrowser

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Iniciar a Lambda Box localmente.")
    parser.add_argument("--no-browser", action="store_true", help="Não abre o navegador automaticamente.")
    parser.add_argument("--port", type=int, default=8090, help="Porta local (padrão: 8090).")
    args = parser.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    # Bind before launching the browser; pass the same socket to avoid a port race.
    with socket.socket() as listener:
        try:
            listener.bind(("127.0.0.1", args.port))
        except OSError:
            parser.exit(1, f"A porta {args.port} está em uso. Feche a suíte anterior ou informe --port 8091.\n")
        listener.listen(128)
        url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        print(f"Lambda Box disponível em {url}\nMantenha este terminal aberto. Ctrl+C encerra a aplicação.", flush=True)
        if not args.no_browser:
            threading.Timer(1, webbrowser.open, args=(url,)).start()
        server = uvicorn.Server(uvicorn.Config("suite.web.application:create_app", factory=True, log_level="info"))
        server.run(sockets=[listener])


if __name__ == "__main__":
    main()
