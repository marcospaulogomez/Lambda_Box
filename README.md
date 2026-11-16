# Suíte de ferramentas (converter e juntar arquivos, gerar qr code)

Projeto em desenvolvimento para aprendizado em Python, portfólio e futura disponibilização à comunidade. O nome e a marca serão definidos posteriormente.

## Estado atual

- **Suíte modular local:** página inicial azul e Word para PDF com upload de DOCX, processamento em lote pelo LibreOffice, acompanhamento da tarefa e downloads individuais ou em ZIP.
- **Ferramentas de PDF:** juntar PDFs e converter e juntar DOCX/PDFs estão disponíveis pelos cartões da página inicial, com seleção, reordenação e download do PDF final.
- **Imagens para PDF:** JPG, JPEG e PNG, uma imagem por página A4, com ordem ajustável, orientação automática e transparências sobre fundo branco. Funciona sem Word ou LibreOffice.
- **QR Code:** links ou texto em PNG, com legenda opcional, prévia e download; funciona sem Word ou LibreOffice.
- **Conversor local funcional:** converte documentos com o Microsoft Word instalado no Windows e permite juntar os resultados.
- **Prévia visual:** grade azul com as cinco ferramentas planejadas; ainda não está integrada ao processamento.
- **Laboratório de conversão:** testa DOCX com LibreOffice, gera exemplos fictícios e registra os resultados para comparação com o Word.

A suíte completa e o serviço público ainda estão em construção. Consulte o [escopo da primeira versão](docs/mvp-scope.md).

## Abrir a suíte em desenvolvimento

Ambiente validado nesta etapa: Windows, Python 3.14 e LibreOffice. Em uma cópia nova do projeto, prepare as dependências:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Instale o [LibreOffice](https://www.libreoffice.org/download/) ou configure `LIBREOFFICE_PATH`. A extração local existente em `laboratory/engine/program/soffice.com` também é detectada automaticamente; essa pasta não acompanha o Git.

```powershell
.\Start_Suite.bat
```

O navegador abre em **http://127.0.0.1:8090**. Escolha **Word para PDF**, **Juntar PDFs**, **Converter e juntar**, **Imagens para PDF** ou **Gerar QR Code**. Nas ferramentas de junção, selecione pelo menos dois arquivos; imagens para PDF aceita a partir de uma imagem. Ajuste a ordem com os botões ↑ e ↓ antes de processar. QR Code recebe link ou texto, com legenda opcional. Mantenha o terminal aberto; Ctrl+C encerra a aplicação. Se a porta estiver ocupada, use `.\Start_Suite.bat --port 8091`.

Nesta versão local: até 10 documentos, 20 MB por arquivo e 50 MB por tarefa; uma conversão por vez, com até quatro tarefas entre envio, espera e processamento. Os PDFs ficam disponíveis por 30 minutos. Os limites são provisórios, definidos em `suite/settings.py`. O serviço público e sua implantação ainda não estão prontos.

Consulte [a base modular e seu roteiro de teste](docs/modular-foundation.md) para entender o código e verificar o fluxo completo.

O [guia de imagens para PDF](docs/images-to-pdf.md) explica formatos, orientação, margens, limites de pixels e o teste reproduzível. Ao atualizar uma cópia existente, instale as dependências de `requirements.txt` e reinicie o servidor.

O [guia de QR Code](docs/qr-code.md) explica o reaproveitamento do gerador desktop, o limite de texto, a legenda e como testar a leitura do PNG.

## Abrir o conversor atual

Requisitos: Windows, Python compatível com as anotações do código (3.10 ou superior) e Microsoft Word instalado. A junção normal no navegador usa PDF-Lib, carregada pela internet.

```powershell
.\Start_Converter.bat
```

O navegador abre automaticamente. Mantenha o terminal aberto enquanto utiliza o aplicativo.

## Abrir a prévia visual

```powershell
.\Preview_Design.bat
```

Essa prévia serve para avaliar a interface. As fontes e os ícones são carregados pela internet; as fontes possuem alternativas locais.

## Executar a prova com LibreOffice

Instale o [LibreOffice](https://www.libreoffice.org/download/) e, para análise das páginas dos PDFs, prepare um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-validation.txt
.\Test_Conversion.bat --diagnostics
.\Test_Conversion.bat
```

O laboratório cria documentos fictícios em `laboratory/samples/` e imprime o caminho do relatório HTML. A pasta `laboratory/` e o ambiente virtual são ignorados pelo Git. Os documentos anteriores foram preservados em `laboratory/input/` e `laboratory/input-v2/`.

Para abrir o último relatório sem converter novamente:

```powershell
.\Test_Conversion.bat --report
```

Consulte o [guia da prova de conversão](docs/conversion-validation.md) para comparar PDFs exportados pelo Word ou testar documentos próprios. A contagem das páginas não substitui a avaliação visual.

## Testes automatizados

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes do adaptador e das rotas usam um motor controlado. Para verificar o servidor em execução com o LibreOffice real:

```powershell
.\.venv\Scripts\python.exe scripts/check_web_flow.py
```

Esse comando gera cinco DOCX fictícios, envia ao servidor local, confere PDFs e ZIP, verifica a exclusão e salva evidências em `laboratory/web-flow/`. A compatibilidade visual deve ser avaliada também com documentos representativos.

## Organização

```text
app.py                    Aplicativo local existente
public/                   Interface do conversor existente
suite/conversion/         Adaptador LibreOffice e gerador de DOCX de teste
suite/qr/                 Gerador de QR Code estático em PNG
suite/services/           Fila de conversão, resultados e arquivos temporários
suite/web/                Rotas FastAPI, templates e arquivos da interface
suite/settings.py         Configurações e limites locais
start_suite.py           Inicialização da suíte modular
scripts/check_web_flow.py  Verificação HTTP com o motor real
validate_conversion.py      Execução do laboratório e geração dos relatórios
tests/                    Testes automatizados
docs/                     Escopo, decisões e orientações
outputs/                  Fontes e exportação da prévia visual
```

Os adaptadores são separados da interface para que os motores possam evoluir sem reescrever as telas. As cinco ferramentas iniciais já possuem fluxos locais; a preparação para hospedagem pública é uma próxima etapa.

Consulte o [backend de operações com PDF](docs/pdf-backend.md) para testar juntar PDFs e converter e juntar. Os nomes dos arquivos e diretórios do projeto agora são em inglês: use `Start_Suite.bat`, `Test_Conversion.bat` e `validate_conversion.py`. Os resultados históricos locais foram preservados em `laboratory/`, com os relatórios chamados `report.html` e `report.json`.
