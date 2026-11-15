# Suíte de ferramentas (converter e juntar arquivos, gerar qr code)

Projeto em desenvolvimento para aprendizado em Python, portfólio e futura disponibilização à comunidade. O nome e a marca serão definidos posteriormente.

## Estado atual

- **Conversor local funcional:** converte documentos com o Microsoft Word instalado no Windows e permite juntar os resultados.
- **Prévia visual:** grade azul com as cinco ferramentas planejadas; ainda não está integrada ao processamento.
- **Laboratório de conversão:** testa DOCX com LibreOffice, gera exemplos fictícios e registra os resultados para comparação com o Word.

A suíte completa e o serviço público ainda estão em construção. Consulte o [escopo da primeira versão](docs/escopo-mvp.md).

## Abrir o conversor atual

Requisitos: Windows, Python compatível com as anotações do código (3.10 ou superior) e Microsoft Word instalado. A junção normal no navegador usa PDF-Lib, carregada pela internet.

```powershell
.\Iniciar_Conversor.bat
```

O navegador abre automaticamente. Mantenha o terminal aberto enquanto utiliza o aplicativo.

## Abrir a prévia visual

```powershell
.\Testar_Visual.bat
```

Essa prévia serve para avaliar a interface. As fontes e os ícones são carregados pela internet; as fontes possuem alternativas locais.

## Executar a prova com LibreOffice

Instale o [LibreOffice](https://www.libreoffice.org/download/) e, para análise das páginas dos PDFs, prepare um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-validacao.txt
.\Testar_Conversao.bat --diagnostico
.\Testar_Conversao.bat
```

O laboratório cria documentos fictícios em `laboratorio/entrada/` e imprime o caminho do relatório HTML. A pasta `laboratorio/` e o ambiente virtual são ignorados pelo Git.

Para abrir o último relatório sem converter novamente:

```powershell
.\Testar_Conversao.bat --relatorio
```

Consulte o [guia da prova de conversão](docs/prova-conversao.md) para comparar PDFs exportados pelo Word ou testar documentos próprios. A contagem das páginas não substitui a avaliação visual.

## Testes automatizados

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes de contrato do adaptador usam um motor simulado. A compatibilidade e a fidelidade devem ser avaliadas também com o LibreOffice instalado e documentos representativos.

## Organização

```text
app.py                    Aplicativo local existente
public/                   Interface do conversor existente
suite/conversion/         Adaptador LibreOffice e gerador de DOCX de teste
validar_conversao.py      Execução do laboratório e geração dos relatórios
tests/                    Testes automatizados
docs/                     Escopo, decisões e orientações
outputs/                  Fontes e exportação da prévia visual
```

O adaptador é separado da interface para que possa ser integrado à futura API sem depender do desenho das telas. A prioridade atual é validar o motor de conversão antes da migração para a base modular completa.
