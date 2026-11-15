# Prova de conversão DOCX → PDF

O objetivo é descobrir se o LibreOffice produz resultados adequados aos documentos que a suíte atenderá. Converter sem erro é apenas a primeira verificação: a aprovação da aparência depende da comparação com o documento aberto no Word.

## O que foi preparado

- Um adaptador Python independente da interface, em `suite/conversion/libreoffice.py`.
- Cinco documentos fictícios gerados pelo próprio projeto: texto e fontes; tabela com cabeçalho e rodapé; imagem; página em paisagem; quebra manual de página.
- Execução sequencial com perfil descartável próprio para cada conversão e prazo por documento.
- Relatório HTML com links para os arquivos e relatório JSON com tempos e tamanhos.
- Análise opcional de páginas e dimensões com pypdf.
- Comparação opcional com PDFs exportados pelo Word.

O aplicativo existente continua usando seu fluxo atual. Esta prova ainda não integra o novo motor às rotas HTTP.

## Preparar o ambiente

Instalar o LibreOffice a partir da [página oficial](https://www.libreoffice.org/download/). O motor roda sem interface gráfica, conforme a [documentação de parâmetros](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html).

Neste ambiente de desenvolvimento, o motor foi extraído para `laboratorio/motor/` para avaliação local, sem uma instalação global. O atalho detecta `laboratorio/motor/program/soffice.com` automaticamente quando `LIBREOFFICE_PATH` não está definida. Essa extração não entra no Git; em outra máquina, instale o LibreOffice ou configure o caminho do executável.

Para incluir a análise estrutural dos PDFs, criar um ambiente virtual e instalar a dependência da prova. Um ambiente virtual é uma pasta que mantém as dependências deste projeto separadas das de outros projetos.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-validacao.txt
```

Não é necessário ativar o ambiente virtual: os comandos usam diretamente seu executável. `Testar_Conversao.bat` também dá preferência a ele.

A conversão pode rodar sem pypdf. Nesse caso, o relatório informa que a análise de páginas não foi executada. O pacote lê a estrutura dos PDFs; ele não valida a fidelidade visual. [Documentação do pypdf](https://pypdf.readthedocs.io/en/stable/).

## Executar

Para verificar a instalação:

```powershell
.\Testar_Conversao.bat --diagnostico
```

Para gerar os documentos e converter todos os exemplos:

```powershell
.\Testar_Conversao.bat
```

O comando imprime o caminho do `relatorio.html`. Abra esse arquivo no navegador, pelo Explorador de Arquivos. Os documentos ficam em `laboratorio/entrada/` e cada execução produz uma subpasta nova em `laboratorio/resultados/`.

Para abrir diretamente o relatório mais recente, sem repetir as conversões:

```powershell
.\Testar_Conversao.bat --relatorio
```

Para gerar somente os originais, mesmo antes de instalar o LibreOffice:

```powershell
.\Testar_Conversao.bat --gerar-exemplos
```

Exemplos já existentes não são sobrescritos. Se quiser começar novamente, use uma cópia dos originais ou remova manualmente apenas os exemplos que deseja regenerar.

Para gerar e converter os exemplos revisados em outra pasta, preservando os anteriores:

```powershell
.\Testar_Conversao.bat --pasta-exemplos .\laboratorio\entrada-v2
```

Os exemplos revisados definem explicitamente entrelinha de 1,15, espaço de 8 pontos após os parágrafos e alinhamento da imagem. O primeiro documento inclui três linhas dentro do mesmo parágrafo, para distinguir entrelinha de distância entre parágrafos. Essa formatação pertence aos documentos fictícios; o adaptador não aplica esses valores aos arquivos enviados pelo usuário.

O relatório agora separa preparação, execução do motor, cópia do PDF e limpeza. O tempo do motor inclui iniciar o processo, preparar o perfil, importar o DOCX, exportar o PDF e encerrar; não mede apenas a renderização.

## Comparar com o Word

1. Abra cada DOCX de `laboratorio/entrada/` no Word e confira que ele está íntegro.
2. Exporte pelo Word para uma pasta `laboratorio/referencias-word/`, mantendo o mesmo nome-base. Por exemplo, `01-texto-e-fontes.docx` deve corresponder a `01-texto-e-fontes.pdf`.
3. Execute:

```powershell
.\Testar_Conversao.bat --referencias .\laboratorio\referencias-word
```

4. No relatório, abra o PDF gerado e a referência. Compare fontes, acentos, margens, tabelas, proporções das imagens, orientação, cabeçalho, rodapé e quebras de página.
5. Registre as diferenças observadas. Uma tabela simples basta: documento, diferença, impacto e aceitação.

O quinto exemplo deve ter duas páginas. Na imagem, as áreas coloridas precisam manter a proporção horizontal de 2:1. O quarto exemplo deve ter uma página em paisagem.

Quantidades e dimensões iguais de páginas não provam que a formatação está igual. Referências ausentes ficam explicitamente indicadas no relatório.

Ao comparar a revisão, use os DOCX de `laboratorio/entrada-v2/` e referências exportadas desses mesmos documentos. Informe `--pasta-exemplos .\laboratorio\entrada-v2` junto com `--referencias` para não converter os exemplos antigos por engano.

## Testar documentos próprios

Use arquivos sem informações confidenciais para os primeiros testes:

```powershell
.\Testar_Conversao.bat --entrada "C:\caminho\documentos"
```

A busca considera apenas os DOCX diretamente nessa pasta e ignora os arquivos temporários do Word iniciados por `~$`. Os originais são copiados para uma área temporária; a conversão não modifica os documentos enviados.

Se o executável não for encontrado automaticamente:

```powershell
.\Testar_Conversao.bat --libreoffice "C:\Program Files\LibreOffice\program\soffice.com"
```

Também é possível definir `LIBREOFFICE_PATH` para esse caminho. Para documentos mais demorados, há `--timeout 180`. O prazo padrão é 90 segundos por arquivo; ele é um limite desta prova local, não uma política final da suíte pública.

## Testes automatizados

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes verificam entradas inválidas, ausência de saída apesar de retorno sem erro, proteção contra sobrescrita, isolamento dos perfis, integridade dos exemplos e relatório. Usam um motor simulado e não comprovam a compatibilidade visual do LibreOffice. O teste real é a execução dos documentos pelo motor instalado.

## Limites desta etapa

- Apenas DOCX; não é uma declaração de suporte a todos os formatos de Office.
- Ainda não foram definidos limites para arquivos públicos, isolamento de uploads hostis ou política final de retenção.
- Perfil separado e prazo de execução não equivalem a um ambiente de segurança para documentos desconhecidos.
- O relatório mede duração e tamanho dos PDFs. Memória, concorrência e capacidade de hospedagem ainda não são medidas.
- Os resultados e documentos do laboratório estão no `.gitignore`, para evitar publicar arquivos locais por acidente. O código gerador e as instruções são versionáveis.
- A escolha final do motor continua pendente até a revisão dos exemplos e de documentos representativos do uso real.
