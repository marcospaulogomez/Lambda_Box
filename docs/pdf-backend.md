# Backend de operações com PDF

Esta entrega implementa juntar PDFs e converter e juntar na API. A interface de Word para PDF continua funcionando. As telas das duas ferramentas serão conectadas em outra entrega, aproveitando o layout aprovado; a reorganização visual está adiada.

## Operações

| Endereço HTTP | Entrada no campo multipart `files` | Resultado |
| --- | --- | --- |
| `POST /api/jobs/word-to-pdf` | 1 a 10 DOCX | PDFs individuais e ZIP para vários resultados |
| `POST /api/jobs/merge-pdfs` | 2 a 10 PDFs | Um `merged.pdf` |
| `POST /api/jobs/convert-and-merge` | 2 a 10 DOCX/PDFs | Um `merged.pdf` |

A ordem dos campos `files` é a ordem final dos documentos. Nomes repetidos são aceitos: internamente, cada arquivo recebe um índice único. O fluxo combinado converte somente os DOCX, em uma execução do LibreOffice, e recoloca cada PDF convertido na posição correspondente. Se só houver PDFs, ele dispensa o motor Office.

As três operações devolvem HTTP 202 com o identificador da tarefa. Consulte `GET /api/jobs/{id}` até receber `completed` ou `failed`. No estado concluído, `files` contém os links e `pages` informa a quantidade total de páginas nos fluxos de junção. Os mesmos endpoints de download, exclusão e expiração atendem às três ferramentas.

## Separação do código

- `suite/pdf/merging.py` lê, valida e junta PDFs. É independente de HTTP e do LibreOffice.
- `suite/services/documents.py` controla a tarefa, mantém a ordem das entradas, chama os adaptadores e prepara os resultados.
- `suite/web/application.py` recebe os uploads e expõe os endpoints.

O motor usa [`PdfWriter.append` do pypdf](https://pypdf.readthedocs.io/en/stable/user/merging-pdfs.html). A operação copia as páginas para o resultado sem convertê-las em imagens. Campos de formulários recebem um prefixo por documento para evitar colisões de nomes. A validação automatizada cobre a ordem, o texto no fluxo real, as dimensões e a rotação das páginas; formulários complexos, assinaturas e documentos fora dessa amostra ainda exigem avaliação específica. Uma junção modifica o documento e não preserva a validade de assinaturas digitais dos originais.

## Validação e limites locais

Continuam valendo 20 MB por arquivo, 50 MB por tarefa e a fila compartilhada com até quatro tarefas ativas, uma em processamento. Há um limite inicial de 500 páginas no resultado, configurável em `Settings.max_pdf_pages`.

PDFs vazios, corrompidos e protegidos por senha são rejeitados. O limite de páginas é conferido nos PDFs recebidos e novamente após converter os DOCX. Se qualquer entrada falhar, o serviço não publica um resultado parcial. Os originais locais não são modificados; as cópias temporárias e PDFs intermediários são removidos ao terminar a tarefa.

O prazo de 180 segundos controla a invocação do LibreOffice. A junção com pypdf roda na fila do processo e ainda não possui um prazo de execução com encerramento forçado. O isolamento de processos e os limites de recursos para documentos públicos permanecem na etapa de hospedagem.

## Como testar

1. Inicie a aplicação com `.\Start_Suite.bat`.
2. Acesse `http://127.0.0.1:8090/docs`, a documentação interativa da API.
3. Abra uma operação POST, clique em **Try it out**, selecione os arquivos e execute.
4. Copie o `id` da resposta e consulte `GET /api/jobs/{job_id}`. Ao concluir, abra o endereço de download retornado em `files`.

Para uma verificação reproduzível, com as dependências de desenvolvimento instaladas e o servidor em execução:

```powershell
.\.venv\Scripts\python.exe scripts/check_web_flow.py --pdf-tools
```

O script testa Word para PDF, a junção de PDFs com nomes repetidos e uma sequência intercalada de PDF/DOCX/PDF. Confere paginação, ordem, texto e dimensões, ZIP e exclusão, preservando evidências em `laboratory/web-flow/`. As dimensões são comparadas com três casas decimais em pontos, pois a serialização do PDF arredonda valores numéricos. Essa verificação estrutural não substitui a revisão visual dos arquivos.

## Resultado desta entrega

Em 15/11/2026, os 42 testes automatizados passaram. A verificação com o servidor HTTP e o LibreOffice reais também passou para as três ferramentas. Na amostra local, Word para PDF levou 27,685 segundos de processamento para cinco documentos; juntar PDFs gerou três páginas em 0,026 segundo; converter e juntar gerou quatro páginas em 24,728 segundos. Os resultados mantiveram a ordem, o texto e a geometria na precisão verificada, e os testes de ZIP e exclusão passaram. O registro local está em `laboratory/web-flow/859d4a6f/report.json`, fora do Git. Os tempos são dessa amostra e não estimam o desempenho da futura hospedagem.
