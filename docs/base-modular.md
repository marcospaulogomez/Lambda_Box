# Base modular e primeiro fluxo funcional

Esta etapa liga o visual azul aprovado a um fluxo completo de Word para PDF. O aplicativo anterior, iniciado por `Iniciar_Conversor.bat`, permanece disponível. A nova suíte usa `Iniciar_Suite.bat` e ainda é uma aplicação local em desenvolvimento.

## Por que separar o código

Uma rota é o endereço que recebe uma solicitação HTTP. Um serviço coordena a tarefa. Um adaptador conversa com a ferramenta externa. Separar essas responsabilidades permite adicionar juntar PDFs ou QR Code sem colocar suas regras dentro da interface ou do motor de documentos.

```text
Navegador: grade → Word para PDF → seleção e envio
    ↓ POST /api/jobs/word-to-pdf
suite/web/application.py: recebe e limita o envio
    ↓
suite/services/documents.py: prepara a tarefa e controla a fila
    ↓
suite/conversion/libreoffice.py: converte o lote com um perfil exclusivo
    ↓
GET /api/jobs/{id}: informa andamento e URLs dos resultados
    ↓
Navegador: download de cada PDF ou do ZIP
```

O [FastAPI aceita uploads multipart](https://fastapi.tiangolo.com/tutorial/request-files/), formato usado pelo formulário. Os [templates Jinja2](https://fastapi.tiangolo.com/advanced/templates/) montam as páginas; CSS e JavaScript cuidam da aparência e das interações. Todo o processamento de documentos permanece em Python e no motor externo.

## O que funciona

- Página inicial com a grade aprovada; somente Word para PDF está disponível nesta etapa.
- Seleção pelo explorador ou por arrastar e soltar, remoção de itens e validação no navegador e no servidor.
- Uma inicialização do LibreOffice para todos os documentos de uma tarefa. Cada tarefa usa um perfil descartável próprio.
- Estados `queued`, `processing`, `completed` e `failed`, consultados pelo navegador sem bloquear a página.
- PDFs individuais e ZIP para lotes com mais de um documento. Os nomes recebem prefixos numéricos, preservando a ordem mesmo com nomes iguais.
- Arquivos originais removidos da área de processamento ao encerrar a conversão; resultados removidos por prazo ou pelo botão de exclusão.
- Recuperação do acompanhamento ao atualizar a aba, por um identificador guardado em `sessionStorage`.

Nomes novos de funções, variáveis, classes e campos da API são em inglês. Textos da interface continuam em português. A tradução dos identificadores antigos será uma refatoração separada.

## Limites e funcionamento da fila

| Configuração local | Valor inicial |
| --- | --- |
| Arquivos por tarefa | 10 DOCX |
| Tamanho de cada arquivo | 20 MB |
| Soma dos arquivos | 50 MB |
| Tarefas ativas, incluindo envios e espera | 4 |
| Conversões simultâneas | 1 |
| Prazo de conversão | 180 segundos para o lote inteiro |
| Disponibilidade dos resultados | 30 minutos após o término |

As configurações estão em `suite/settings.py`. O corpo HTTP tem limite adicional de 1 MB para os metadados multipart. O pacote DOCX também tem limites de quantidade de entradas e de tamanho declarado descompactado. Isso não equivale a um isolamento para documentos hostis.

A fila é um `ThreadPoolExecutor` com um trabalhador. Ele mantém o processo pesado fora do atendimento HTTP. Antes de aceitar uma tarefa, o serviço verifica a capacidade; uma fila cheia devolve HTTP 429. Não há porcentagem fictícia de conversão.

As tarefas ficam na memória de **um único processo**. Não iniciar vários workers Uvicorn nesta versão: cada um teria uma fila e arquivos diferentes. Reiniciar o servidor perde os identificadores anteriores. Uma futura implantação com múltiplos processos precisará compartilhar fila, metadados e armazenamento.

A limpeza periódica roda a cada 60 segundos. O download deixa de ser aceito ao expirar o prazo; uma transmissão já iniciada pode terminar antes da remoção física. Encerramentos normais limpam a pasta temporária da sessão, aguardando a conversão ativa e cancelando tarefas ainda na fila. Uma interrupção abrupta do processo pode deixar temporários no sistema operacional; recuperação após falhas permanece pendente para a publicação.

O lote é disponibilizado apenas se todos os PDFs forem gerados. Se um documento falhar, a tarefa informa erro e não oferece um conjunto incompleto. Não há cancelamento de conversões em execução nesta etapa.

O serviço escuta somente em `127.0.0.1`; os hosts e as origens aceitos também estão restritos ao uso local. Os identificadores aleatórios das tarefas dão acesso aos downloads a quem os possuir. Não há contas de usuário ou armazenamento persistente. Antes de abrir ao público, faltam isolamento do motor, avaliação de memória e concorrência, política de retenção em produção e configuração da hospedagem.

## Testar no navegador

1. Execute `.\Iniciar_Suite.bat` na raiz e acesse a página aberta em `http://127.0.0.1:8090`.
2. Entre em **Word para PDF** e selecione os cinco DOCX de `laboratorio/entrada-v2/`.
3. Confira nomes e tamanhos, remova e adicione um documento novamente.
4. Clique em **Converter para PDF** e acompanhe os estados de fila e processamento.
5. Baixe os PDFs e o ZIP. Confira a paginação esperada: 1, 1, 1, 1 e 2 páginas. Compare a aparência com os mesmos DOCX no Word.
6. Atualize a aba e confira a recuperação dos resultados. Use **Excluir arquivos desta tarefa** e confirme que os links deixam de funcionar.
7. Teste um arquivo vazio, uma extensão diferente e um arquivo renomeado para DOCX. A mensagem deve explicar o problema sem iniciar a conversão.

**Nova conversão** libera o formulário para outro envio; os resultados anteriores continuam sujeitos ao prazo de retenção. **Excluir arquivos desta tarefa** remove os resultados antes de liberar o formulário.

## Verificação reproduzível com o motor real

Com as dependências de desenvolvimento instaladas e o servidor em execução:

```powershell
.\.venv\Scripts\python.exe scripts/check_web_flow.py
```

Se usar outra porta, passe `--url http://127.0.0.1:8091`. O script usa documentos fictícios gerados por ele e salva as evidências em uma pasta nova de `laboratorio/fluxo-web/`, ignorada pelo Git. As cópias de verificação nessa pasta permanecem para análise; a exclusão testada é a dos arquivos temporários do serviço.

Na execução local de 15/11/2026, os cinco DOCX passaram pelo servidor HTTP real e pelo LibreOffice em lote: 35,558 segundos no adaptador e 36,879 segundos entre início do envio e obtenção do estado concluído. Os PDFs tiveram 1, 1, 1, 1 e 2 páginas. O ZIP correspondeu byte a byte aos downloads individuais, os originais permaneceram iguais e a exclusão bloqueou os downloads seguintes. Evidências locais: `laboratorio/fluxo-web/c9e9fa94/report.json`.

Esses tempos não estimam a capacidade de uma hospedagem pública. A revisão visual pelo usuário continua necessária; a contagem de páginas não comprova fidelidade de formatação.

Também foram executados 32 testes automatizados de contrato e integração HTTP. Na conferência com Chrome, a seleção dos cinco documentos, a conversão e a exclusão pela interface passaram sem exceções JavaScript capturadas. A tela e os resultados foram conferidos com viewport de 390 px, sem rolagem horizontal; a grade inicial também foi conferida em desktop. Capturas locais ficam em `laboratorio/preview-suite/`.
