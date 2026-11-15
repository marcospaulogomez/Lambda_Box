"""Gera documentos fictícios para a prova, usando somente a biblioteca padrão."""

from html import escape
from pathlib import Path
import struct
import zlib
import zipfile

NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
# 276/240 = 1,15 linha; 160/20 = 8 pontos depois de cada parágrafo.
PARAGRAPH_PROPERTIES = '<w:pPr><w:spacing w:before="0" w:after="160" w:line="276" w:lineRule="auto"/><w:ind w:left="0" w:right="0" w:firstLine="0"/><w:jc w:val="left"/></w:pPr>'
STYLES = XML + f'<w:styles {NS}><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="24"/></w:rPr></w:rPrDefault><w:pPrDefault>{PARAGRAPH_PROPERTIES}</w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>{PARAGRAPH_PROPERTIES}</w:style></w:styles>'


def paragraph(text: str, *, bold: bool = False, font: str = "Arial", size: int = 24) -> str:
    properties = f'<w:rFonts w:ascii="{escape(font, quote=True)}" w:hAnsi="{escape(font, quote=True)}"/><w:sz w:val="{size}"/>'
    lines = '<w:br/>'.join(f'<w:t xml:space="preserve">{escape(line)}</w:t>' for line in text.split('\n'))
    return f'<w:p>{PARAGRAPH_PROPERTIES}<w:r><w:rPr>{properties}{"<w:b/>" if bold else ""}</w:rPr>{lines}</w:r></w:p>'


def _picture_paragraph() -> str:
    return f'''<w:p>{PARAGRAPH_PROPERTIES}<w:r><w:drawing>
<wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" distT="0" distB="0" distL="0" distR="0">
<wp:extent cx="3657600" cy="1828800"/><wp:effectExtent l="0" t="0" r="0" b="0"/>
<wp:docPr id="1" name="Padrão de proporção 2:1"/>
<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="0" name="padrao.png"/><pic:cNvPicPr/></pic:nvPicPr>
<pic:blipFill><a:blip r:embed="rIdImage"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="3657600" cy="1828800"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'''


def _test_png() -> bytes:
    # Padrão assimétrico: ajuda a identificar rotação, distorção e corte.
    width, height = 160, 80
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            rows.extend((36, 92, 150) if x < 100 else ((230, 175, 60) if y < 40 else (120, 165, 115)))
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(rows))) + chunk(b"IEND", b"")


def generate_samples(directory: Path) -> list[Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    table = '<w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/><w:tblBorders>' + ''.join(f'<w:{side} w:val="single" w:sz="6"/>' for side in ("top", "left", "bottom", "right", "insideH", "insideV")) + '</w:tblBorders></w:tblPr><w:tblGrid><w:gridCol w:w="4500"/><w:gridCol w:w="4500"/></w:tblGrid>'
    for left, right in [("Item", "Descrição"), ("Documento", "Conversão de teste"), ("Acentuação", "Informação, ação e São Paulo"), ("Valor", "R$ 1.234,56")]:
        table += '<w:tr>' + ''.join(f'<w:tc><w:tcPr><w:tcW w:w="4500" w:type="dxa"/></w:tcPr>{paragraph(value)}</w:tc>' for value in (left, right)) + '</w:tr>'
    table += '</w:tbl>'
    picture = _picture_paragraph()
    cases = [
        ("01-texto-e-fontes.docx", paragraph("Texto e fontes", bold=True, size=36) + paragraph("Informação, conversão, ação, ç, á, ê e R$ 1.234,56.") + paragraph("Arial: confira acentos e alinhamento.") + paragraph("Times New Roman: confira a troca de fonte.", font="Times New Roman") + paragraph("Linhas no mesmo parágrafo (1,15):\nSegunda linha para comparação.\nTerceira linha para comparação."), False, False),
        ("02-tabela-e-cabecalho.docx", paragraph("Tabela com cabeçalho e rodapé", bold=True, size=32) + table + paragraph("Confira as bordas, as colunas e a numeração de página."), False, False),
        ("03-imagem-e-proporcao.docx", paragraph("Imagem com proporção 2:1", bold=True, size=32) + picture + paragraph("O retângulo deve manter as três áreas coloridas e a proporção horizontal."), False, True),
        ("04-paisagem.docx", paragraph("Página em paisagem", bold=True, size=32) + paragraph("Confira orientação horizontal e margens.") + table, True, False),
        ("05-quebra-de-pagina.docx", paragraph("Primeira página", bold=True, size=32) + paragraph("Este documento deve ter exatamente duas páginas.") + '<w:p><w:r><w:br w:type="page"/></w:r></w:p>' + paragraph("Segunda página", bold=True, size=32) + paragraph("Confira a quebra manual e a numeração no rodapé."), False, False),
    ]
    created = []
    for name, body, landscape, image in cases:
        destination = directory / name
        # Não altera documentos que o usuário já tenha editado para seus testes.
        if destination.exists():
            created.append(destination)
            continue
        page = '<w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>' if landscape else '<w:pgSz w:w="11906" w:h="16838"/>'
        section = f'<w:sectPr><w:headerReference w:type="default" r:id="rIdHeader"/><w:footerReference w:type="default" r:id="rIdFooter"/>{page}<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720"/></w:sectPr>'
        types = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>'
        rels = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdHeader" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/><Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>' + ('<Relationship Id="rIdImage" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/padrao.png"/>' if image else '') + '</Relationships>'
        types = types.replace('</Types>', '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
        rels = rels.replace('</Relationships>', '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        with destination.open("xb") as stream, zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as package:
            package.writestr("[Content_Types].xml", XML + types)
            package.writestr("_rels/.rels", XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
            package.writestr("word/document.xml", XML + f'<w:document {NS}><w:body>{body}{section}</w:body></w:document>')
            package.writestr("word/styles.xml", STYLES)
            package.writestr("word/_rels/document.xml.rels", XML + rels)
            package.writestr("word/header1.xml", XML + f'<w:hdr {NS}>{paragraph("SUÍTE — DOCUMENTO FICTÍCIO DE VALIDAÇÃO", size=18)}</w:hdr>')
            package.writestr("word/footer1.xml", XML + f'<w:ftr {NS}><w:p><w:r><w:t>Página </w:t></w:r><w:fldSimple w:instr="PAGE"/></w:p></w:ftr>')
            if image:
                package.writestr("word/media/padrao.png", _test_png())
        created.append(destination)
    return created
