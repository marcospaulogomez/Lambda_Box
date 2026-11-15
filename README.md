# Suíte de ferramentas (converter e juntar arquivos, gerar qr code)

Projeto em desenvolvimento para aprendizado em Python, portfólio e futura disponibilização à comunidade. O nome e a marca serão definidos posteriormente.

## Estado atual

- **Suíte modular local:** página inicial azul e Word para PDF com upload de DOCX, processamento em lote pelo LibreOffice, acompanhamento da tarefa e downloads individuais ou em ZIP.
- **Conversor local funcional:** converte documentos com o Microsoft Word instalado no Windows e permite juntar os resultados.
- **Prévia visual:** grade azul com as cinco ferramentas planejadas; ainda não está integrada ao processamento.
- **Laboratório de conversão:** testa DOCX com LibreOffice, gera exemplos fictícios e registra os resultados para comparação com o Word.

A suíte completa e o serviço público ainda estão em construção. Consulte o [escopo da primeira versão](docs/escopo-mvp.md).

## Abrir a suíte em desenvolvimento

Ambiente validado nesta etapa: Windows, Python 3.14 e LibreOffice. Em uma cópia nova do projeto, prepare as dependências:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Instale o [LibreOffice](https://www.libreoffice.org/download/) ou configure `LIBREOFFICE_PATH`. A extração local existente em `laboratorio/motor/program/soffice.com` também é detectada automaticamente; essa pasta não acompanha o Git.

```powershell
.\Iniciar_Suite.bat
```

O navegador abre em **http://127.0.0.1:8090**. Clique em **Word para PDF**, selecione DOCX e converta. Os outros quatro cartões indicam ferramentas planejadas. Mantenha o terminal aberto; Ctrl+C encerra a aplicação. Se a porta estiver ocupada, use `.\Iniciar_Suite.bat --port 8091`.

Nesta versão local: até 10 documentos, 20 MB por arquivo e 50 MB por tarefa; uma conversão por vez, com até quatro tarefas entre envio, espera e processamento. Os PDFs ficam disponíveis por 30 minutos. Os limites são provisórios, definidos em `suite/settings.py`. O serviço público e sua implantação ainda não estão prontos.

Consulte [a base modular e seu roteiro de teste](docs/base-modular.md) para entender o código e verificar o fluxo completo.

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
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes do adaptador e das rotas usam um motor controlado. Para verificar o servidor em execução com o LibreOffice real:

```powershell
.\.venv\Scripts\python.exe scripts/check_web_flow.py
```

Esse comando gera cinco DOCX fictícios, envia ao servidor local, confere PDFs e ZIP, verifica a exclusão e salva evidências em `laboratorio/fluxo-web/`. A compatibilidade visual deve ser avaliada também com documentos representativos.

## Organização

```text
app.py                    Aplicativo local existente
public/                   Interface do conversor existente
suite/conversion/         Adaptador LibreOffice e gerador de DOCX de teste
suite/services/           Fila de conversão, resultados e arquivos temporários
suite/web/                Rotas FastAPI, templates e arquivos da interface
suite/settings.py         Configurações e limites locais
iniciar_suite.py           Inicialização da suíte modular
scripts/check_web_flow.py  Verificação HTTP com o motor real
validar_conversao.py      Execução do laboratório e geração dos relatórios
tests/                    Testes automatizados
docs/                     Escopo, decisões e orientações
outputs/                  Fontes e exportação da prévia visual
```

O adaptador é separado da interface para que o motor possa evoluir sem reescrever as telas. A base modular já atende Word para PDF; as demais ferramentas serão integradas por etapas.
