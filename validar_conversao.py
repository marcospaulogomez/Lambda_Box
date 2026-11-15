"""Laboratório local de DOCX para PDF. Não inicia o servidor do aplicativo."""

import argparse
from datetime import datetime
from html import escape
import importlib.util
import json
from pathlib import Path
import platform
import sys
import uuid
import webbrowser

from suite.conversion import ConversionError, LibreOfficeConverter
from suite.conversion.samples import generate_samples

BASE_DIR = Path(__file__).resolve().parent


def inspect_pdf(path: Path) -> dict:
    """A análise estrutural não substitui a comparação de aparência."""
    if importlib.util.find_spec("pypdf") is None:
        return {"paginas": None, "analise": "pypdf não instalado; contagem e leitura não executadas"}
    from pypdf import PdfReader

    with path.open("rb") as stream:
        reader = PdfReader(stream)
        return {
            "paginas": len(reader.pages),
            "dimensoes_pt": [[round(float(page.mediabox.width), 2), round(float(page.mediabox.height), 2)] for page in reader.pages],
            "analise": "PDF lido; aparência ainda precisa de avaliação visual",
        }


def write_report(directory: Path, report: dict) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "relatorio.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = []
    for item in report["arquivos"]:
        source_link = f'<a href="{escape(Path(item["entrada"]).as_uri(), quote=True)}">DOCX</a>'
        pdf_link = f'<a href="{escape(Path(item["pdf"]).as_uri(), quote=True)}">PDF gerado</a>' if item.get("pdf") else "—"
        reference_link = f' · <a href="{escape(Path(item["referencia"]).as_uri(), quote=True)}">PDF do Word</a>' if item.get("referencia") else ""
        timing = item.get("tempos_etapas", {})
        labels = {"preparacao": "Preparação", "motor": "Motor", "publicacao": "Cópia do PDF", "limpeza": "Limpeza"}
        breakdown = '<br><small>' + ' · '.join(f'{labels[key]}: {float(timing[key]):.3f}s' for key in labels if key in timing) + '</small>' if timing else ''
        rows.append(f'<tr><td>{escape(item["nome"])}</td><td>{escape(item["status"])}</td><td>{item.get("segundos", "—")}{breakdown}</td><td>{item.get("paginas") if item.get("paginas") is not None else "—"}</td><td>{source_link} · {pdf_link}{reference_link}</td><td>{escape(item.get("erro") or item.get("comparacao") or item.get("analise", ""))}</td></tr>')
    html = f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Prova de conversão</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;max-width:1200px;margin:32px auto;padding:0 20px;color:#182435;background:#f4f6f8}}h1{{line-height:1.2}}a{{color:#1c57a3}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #cad1db;overflow-wrap:anywhere}}.scroll{{overflow-x:auto}}small{{color:#465569}}@media(max-width:600px){{body{{margin:18px auto}}}}</style></head>
<body><h1>Prova de conversão</h1><p>{escape(report["motor"])} · {escape(report["criado_em"])}</p>
<p><strong>Avaliação visual pendente.</strong> Abra os PDFs e compare fontes, margens, tabelas, imagens e quebras de página com os documentos no Word.</p>
<div class="scroll"><table><thead><tr><th>Documento</th><th>Conversão</th><th>Tempo (s)</th><th>Páginas</th><th>Arquivos</th><th>Observação</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>
<p>Contagens e dimensões iguais não garantem a mesma formatação. Os tempos são de execuções sequenciais locais, incluindo a inicialização do motor.</p>
<small>Memória e concorrência não foram medidas nesta prova. O arquivo relatorio.json guarda os resultados desta execução.</small></body></html>'''
    destination = directory / "relatorio.html"
    destination.write_text(html, encoding="utf-8")
    return destination


def main(argv: list[str] | None = None) -> int:
    # Evita falhas com acentos, símbolos e nomes de arquivos em consoles legados.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Prova local de conversão DOCX → PDF com LibreOffice.")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--diagnostico", action="store_true", help="Mostra o ambiente sem converter arquivos.")
    modes.add_argument("--gerar-exemplos", action="store_true", help="Cria documentos fictícios e encerra.")
    modes.add_argument("--relatorio", action="store_true", help="Abre o relatório mais recente no navegador, sem converter.")
    parser.add_argument("--entrada", type=Path, help="Pasta com DOCX próprios; não gera exemplos nessa pasta.")
    parser.add_argument("--pasta-exemplos", type=Path, default=BASE_DIR / "laboratorio" / "entrada", help="Pasta para gerar e usar exemplos fictícios, preservando os já existentes.")
    parser.add_argument("--saida", type=Path, default=BASE_DIR / "laboratorio" / "resultados", help="Pasta-base de resultados; cada execução cria uma subpasta.")
    parser.add_argument("--referencias", type=Path, help="Pasta de PDFs exportados no Word com os mesmos nomes dos DOCX.")
    parser.add_argument("--libreoffice", type=Path, help="Caminho do soffice.com/soffice, se instalado em outro local.")
    parser.add_argument("--timeout", type=float, default=90, help="Prazo em segundos por documento; padrão: 90.")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout deve ser maior que zero")
    if args.relatorio:
        reports = list(args.saida.glob("*/relatorio.html"))
        if not reports:
            print("Nenhum relatório encontrado. Execute Testar_Conversao.bat primeiro.")
            return 2
        latest = max(reports, key=lambda path: path.stat().st_mtime).resolve()
        print(f"Relatório: {latest}")
        if not webbrowser.open(latest.as_uri()):
            print("Não foi possível abrir o navegador automaticamente. Abra o arquivo acima.")
            return 1
        return 0
    converter = LibreOfficeConverter(args.libreoffice, timeout=args.timeout)
    if args.diagnostico:
        print(f"Python: {platform.python_version()}")
        print(f"Executável Python: {sys.executable}")
        print(f"LibreOffice: {converter.executable or 'NÃO ENCONTRADO'}")
        print(f"Análise de páginas (pypdf): {'disponível' if importlib.util.find_spec('pypdf') else 'não instalada (opcional)'}")
        if converter.executable:
            try:
                print(converter.version())
            except ConversionError as exc:
                print(f"ERRO: {exc}")
                return 1
        return 0 if converter.executable else 2

    input_dir = (args.entrada or args.pasta_exemplos).resolve()
    if args.gerar_exemplos:
        if args.entrada is not None:
            parser.error("--gerar-exemplos usa --pasta-exemplos; não combine com --entrada")
        for path in generate_samples(input_dir):
            print(path)
        print("Documentos fictícios prontos. Abra-os no Word para conferir os originais.")
        return 0
    if args.entrada is None:
        generate_samples(input_dir)
    if not input_dir.is_dir():
        print(f"ERRO: pasta de entrada não encontrada: {input_dir}")
        return 2
    if args.referencias is not None and not args.referencias.is_dir():
        print(f"ERRO: pasta de referências não encontrada: {args.referencias}")
        return 2
    sources = sorted((path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() == ".docx" and not path.name.startswith("~$")), key=lambda path: path.name.casefold())
    if not sources:
        print(f"ERRO: nenhum DOCX encontrado em {input_dir}")
        return 2
    if converter.executable is None:
        print("LibreOffice não encontrado. Os DOCX de exemplo estão prontos em:")
        print(input_dir)
        print("Instale o LibreOffice e execute novamente. Orientações: docs/prova-conversao.md")
        return 2
    try:
        version = converter.version()
    except ConversionError as exc:
        print(f"ERRO: {exc}")
        return 1
    stamp = datetime.now().astimezone()
    run_dir = args.saida.resolve() / f"{stamp:%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
    report = {"criado_em": stamp.isoformat(timespec="seconds"), "python": platform.python_version(), "motor": version, "revisao_visual": "pendente", "memoria": "não medida", "concorrencia": "não testada", "arquivos": []}
    failed = False
    for index, source in enumerate(sources, start=1):
        print(f"[{index}/{len(sources)}] {source.name}", flush=True)
        item = {"nome": source.name, "entrada": str(source), "status": "falha", "revisao_visual": "pendente"}
        try:
            result = converter.convert(source, run_dir / f"{index:03d}")
            item.update({"status": "convertido", "pdf": str(result.output), "segundos": result.seconds, "bytes": result.size_bytes, "tempos_etapas": result.timings})
            try:
                item.update(inspect_pdf(result.output))
            except Exception as exc:
                item.update({"status": "análise falhou", "erro": f"O PDF foi gerado, mas sua leitura falhou: {exc}"})
                failed = True
            if args.referencias:
                reference = (args.referencias / f"{source.stem}.pdf").resolve()
                if reference.is_file():
                    item["referencia"] = str(reference)
                    try:
                        baseline = inspect_pdf(reference)
                        item["paginas_referencia"] = baseline["paginas"]
                        if item.get("paginas") is not None and baseline["paginas"] is not None:
                            same = item["paginas"] == baseline["paginas"] and item["dimensoes_pt"] == baseline["dimensoes_pt"]
                            item["comparacao"] = "Páginas e dimensões coincidem; confira a aparência." if same else "Diferença na quantidade ou dimensão das páginas; confira a aparência."
                        else:
                            item["comparacao"] = "Referência disponível; instale pypdf para comparar páginas."
                    except Exception as exc:
                        item["comparacao"] = f"Não foi possível analisar a referência: {exc}"
                        failed = True
                else:
                    item["comparacao"] = "PDF de referência não encontrado; comparação não executada."
        except (ConversionError, OSError) as exc:
            item["erro"] = str(exc)
            failed = True
        report["arquivos"].append(item)
        print(f"  {item['status']}: {item.get('erro') or item.get('segundos', '—')}", flush=True)
    report_path = write_report(run_dir, report)
    print(f"\nRelatório: {report_path}")
    print("Compare visualmente os resultados antes de aprovar o motor de conversão.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
