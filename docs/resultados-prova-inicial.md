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

Os arquivos gerados e o relatório detalhado permanecem em `laboratorio/`, fora do Git. Para reproduzir, siga o [guia da prova](prova-conversao.md).
