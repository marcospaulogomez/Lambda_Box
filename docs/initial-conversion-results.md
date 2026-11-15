# Resultado técnico inicial da conversão

Execução local em Windows, em 14/11/2026, com Python 3.14.0, LibreOffice 26.8.3.1 e pypdf 7.1.0. O LibreOffice foi extraído para a pasta de laboratório do projeto. O instalador foi conferido pelo SHA256 publicado na distribuição oficial e no manifesto do winget.

## Resultados observados

| Documento fictício | Páginas | Tempo local (s) | PDF (bytes) |
| --- | ---: | ---: | ---: |
| Texto e fontes | 1 | 72,735 | 73.920 |
| Tabela e cabeçalho | 1 | 40,719 | 63.309 |
| Imagem e proporção | 1 | 73,926 | 55.614 |
| Paisagem | 1 | 36,916 | 62.898 |
| Quebra de página | 2 | 32,433 | 56.682 |

Os cinco PDFs puderam ser lidos pelo pypdf. A orientação da página em paisagem foi confirmada pelas dimensões; a presença de uma imagem incorporada foi verificada na estrutura do terceiro PDF; a quebra manual do quinto exemplo produziu duas páginas. A extração de texto do primeiro exemplo manteve a acentuação consultada.

Os tempos incluem a operação local do adaptador, com criação de perfil exclusivo, inicialização do motor, cópia do resultado e limpeza dos temporários. Não há uma estimativa de capacidade de hospedagem a partir desses números. Memória e concorrência não foram medidas.

## O que ainda falta validar

- Comparação visual com os documentos abertos no Word e com PDFs exportados por ele.
- Fidelidade de fontes, margens, posição das imagens, bordas e tamanhos das tabelas, cabeçalhos e rodapés.
- Documentos representativos do uso real, além dos cinco exemplos simples.
- Desempenho no ambiente que será escolhido para hospedagem e estratégia de reaproveitamento de processos, caso necessária.

O motor ainda não está aprovado para a suíte pública. A prova confirma que a conversão pode ser executada localmente e que os resultados passaram nas verificações estruturais descritas.

Os arquivos gerados e o relatório detalhado permanecem em `laboratory/`, fora do Git. Para reproduzir, siga o [guia da prova](conversion-validation.md).

## Revisão após avaliação visual — 15/11/2026

O usuário observou espaçamento menor no PDF e deslocamento da imagem para a direita. Os DOCX fictícios da primeira versão não definiam explicitamente espaçamento de parágrafos, estilos padrão nem distâncias da imagem. A ausência desses valores deixava a apresentação dependente da interpretação de cada editor; isso é uma hipótese para a diferença de espaçamento, ainda sem comparação com um PDF exportado pelo Word.

A revisão do gerador passou a definir entrelinha de 1,15 e espaço de 8 pontos após os parágrafos, além de alinhamento à esquerda e distâncias zeradas na imagem. Conforme a [documentação do formato WordprocessingML](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.spacingbetweenlines?view=openxml-3.0.1), o espaçamento pode ser herdado dos estilos quando não está definido no parágrafo.

Na estrutura do PDF anterior, a imagem começava aproximadamente 3,16 mm à direita do início do texto. No PDF revisado, a diferença horizontal medida foi de cerca de 0,035 mm. Essa medição verifica a posição nesse exemplo simples; não substitui a comparação visual no Word nem demonstra fidelidade para documentos arbitrários.

Os novos originais ficam em `laboratory/input-v2/`; os anteriores foram preservados. O relatório da conversão revisada é `laboratory/results/20261115-135032-12e0b9a2/report.html`. As páginas continuaram em 1, 1, 1, 1 e 2, respectivamente. Os 18 testes automatizados passaram. A aprovação visual da revisão continua pendente.

### Desempenho local

O relatório avaliado pelo usuário (`20261115-132520-10494bf0`) somou 135,581 segundos para cinco documentos. Na revisão, com a medição por etapas, foram observados:

| Documento revisado | Total (s) | Execução do motor (s) |
| --- | ---: | ---: |
| Texto e fontes | 31,326 | 31,179 |
| Tabela e cabeçalho | 30,430 | 30,320 |
| Imagem e proporção | 26,010 | 25,702 |
| Paisagem | 26,102 | 26,001 |
| Quebra de página | 23,271 | 23,165 |
| **Total** | **137,139** | **136,367** |

Mais de 99% desse tempo ficou na execução do LibreOffice. Preparação, publicação do PDF e limpeza somaram menos de um segundo para o conjunto. A medição não separa inicialização de importação e exportação.

Uma experiência local com os mesmos cinco DOCX revisados em uma única invocação do LibreOffice levou 32,549 segundos no total, com 32,337 segundos no motor. Os PDFs foram lidos pelo pypdf e mantiveram as contagens de páginas esperadas. O registro ficou em `laboratory/batch-benchmark/a74c071d/measurement.json`.

Foi uma execução exploratória, aproximadamente 76% mais rápida que a execução separada desses exemplos. Ela indica que evitar reinicializações é um caminho promissor, mas não mede concorrência, memória, fidelidade visual do lote ou capacidade do futuro servidor. O adaptador e o laboratório continuam usando uma execução por arquivo. O processamento em lote ainda precisa ser implementado e validado, incluindo tratamento de falhas por documento e isolamento de tarefas de usuários diferentes.
