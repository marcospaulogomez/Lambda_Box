"""Presentation settings shared by the tool grid and the document workspace."""

DOCUMENT_TOOLS = {
    "word-to-pdf": {
        "title": "Word para PDF", "icon": "word", "category": "DOCUMENTOS", "color": "#9fbff2",
        "card_description": "Converta arquivos Word em PDFs individuais.", "flow": "WORD → PDF",
        "description": "Um PDF por documento, com download individual ou de todos em ZIP.",
        "accept": ".docx", "formats": "DOCX", "min_files": 1, "reorder": True,
        "action": "Converter para PDF", "progress": "Convertendo seus documentos", "result": "Seus PDFs estão prontos",
    },
    "merge-pdfs": {
        "title": "Juntar PDFs", "icon": "merge", "category": "PDF", "color": "#e9a48d",
        "card_description": "Una seus PDFs na ordem que escolher.", "flow": "VÁRIOS PDFs → UM PDF",
        "description": "Escolha seus PDFs, ajuste a ordem e baixe um único arquivo.",
        "accept": ".pdf", "formats": "PDF", "min_files": 2, "reorder": True,
        "action": "Juntar PDFs", "progress": "Juntando seus PDFs", "result": "Seu PDF está pronto",
    },
    "convert-and-merge": {
        "title": "Converter e juntar", "icon": "combine", "category": "DOCUMENTOS / PDF", "color": "#e9a48d",
        "card_description": "Converta documentos Word e junte com seus PDFs.", "flow": "WORD / PDF → UM PDF",
        "description": "Combine documentos Word e PDFs em um único arquivo, na ordem que escolher.",
        "accept": ".docx,.pdf", "formats": "DOCX e PDF", "min_files": 2, "reorder": True,
        "action": "Converter e juntar", "progress": "Convertendo e juntando seus documentos", "result": "Seu PDF está pronto",
    },
    "images-to-pdf": {
        "title": "Imagens para PDF", "icon": "image", "category": "IMAGENS", "color": "#9ac8ad",
        "card_description": "Transforme suas imagens em páginas de um PDF.", "flow": "IMAGENS → PDF",
        "description": "Escolha suas imagens, ajuste a ordem e baixe um único PDF.",
        "accept": ".jpg,.jpeg,.png", "formats": "JPG, JPEG e PNG", "min_files": 1, "reorder": True,
        "selection_title": "Escolha suas imagens",
        "hint": "Uma imagem por página A4, sem cortes, com orientação automática e margem de 12 mm. Transparências ficam com fundo branco.",
        "action": "Gerar PDF", "progress": "Preparando suas imagens", "result": "Seu PDF está pronto",
    },
}
