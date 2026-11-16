# Primeira versão da suíte

## Prioridade e estado atual

A prioridade é construir o software. Nome, logo, favicon, ícones próprios e animações serão retomados depois. A aparência azul aprovada é a base provisória da interface.

MVP significa primeira versão utilizável: um conjunto limitado de ferramentas com resultados verificáveis e um fluxo completo de entrada, processamento e download.

Hoje existem três partes distintas:

- **Aplicativo funcional:** `app.py` e `public/`, iniciados por `Start_Converter.bat`. Automatiza o Word instalado no Windows e oferece o fluxo de converter e juntar. A junção normalmente usa PDF-Lib no navegador.
- **Prévia da suíte:** `outputs/suite-design-preview.html`, exportada para `outputs/design-preview.html` e aberta por `Preview_Design.bat`. Exibe as cinco ferramentas, mas ainda não realiza operações com arquivos.
- **Suíte modular local:** `suite/web/`, iniciada por `Start_Suite.bat`, com a grade inicial e as cinco ferramentas funcionais.

A suíte está disponível em `Start_Suite.bat`: grade inicial com Word para PDF, juntar PDFs, converter e juntar, imagens para PDF e QR Code, com processamento e downloads. Consulte [a base modular](modular-foundation.md) para entender a implementação.

Juntar PDFs e converter e juntar podem ser usados diretamente pelos cartões, com botões para reordenar os arquivos antes do envio. Consulte [as operações com PDF](pdf-backend.md).

Imagens para PDF também funciona pelo cartão, com JPG, JPEG e PNG em páginas A4, preservando a proporção e ajustando a orientação. Consulte [o guia de imagens](images-to-pdf.md).

Este documento define o que será implementado; não declara que a suíte funcional já está pronta.

O laboratório da primeira etapa está disponível em `Test_Conversion.bat`. Consulte [a prova de conversão](conversion-validation.md) para gerar exemplos, verificar o LibreOffice e registrar os resultados. A aprovação do motor continua pendente de testes reais e comparação visual.

## Ferramentas e critérios de conclusão

| Ferramenta | Entrada inicial proposta | Resultado esperado | Verificação principal |
| --- | --- | --- | --- |
| Word para PDF | Um ou mais DOCX | PDF individual por documento; ZIP para download em lote | Abrir os PDFs e comparar paginação, tabelas, imagens e fontes com os originais |
| Juntar PDFs | Dois ou mais PDFs | Um PDF com as páginas na ordem definida | Conferir ordem, número de páginas e dimensões das páginas |
| Converter e juntar | DOCX e PDFs existentes | Um PDF final respeitando a ordem dos arquivos | Conferir a posição de cada documento e a preservação das páginas dos PDFs enviados |
| Imagens para PDF | JPG e PNG | Um PDF com as imagens na ordem escolhida | Conferir proporções, orientação e ordem, sem cortar a imagem por acidente |
| QR Code | Link ou texto | QR Code estático para baixar em PNG | Ler o código no celular e conferir o conteúdo recuperado |

DOCX é a proposta inicial para reduzir a matriz de validação. O conversor atual aceita outros formatos; o suporte deles na nova suíte será decidido com testes, sem retirar recursos do aplicativo atual nesta etapa.

O gerador de QR Code existente foi localizado e sua lógica foi adaptada para a suíte: links ou texto, legenda opcional, prévia e PNG para download, sem motor Office. Consulte [o guia de QR Code](qr-code.md). Um QR Code estático armazena diretamente o conteúdo e dispensa um serviço de redirecionamento próprio.

## Comportamentos compartilhados

- Escolher a ferramenta pela grade inicial.
- Adicionar arquivos e remover os enviados por engano.
- Reordenar arquivos quando a operação depender da sequência, com alternativa acessível por botões.
- Validar tipos, conteúdo e limites antes do processamento.
- Exibir estados claros de preparação, processamento, conclusão e erro.
- Disponibilizar o download com nomes previsíveis, incluindo arquivos de nomes repetidos nos lotes.
- Isolar arquivos temporários por tarefa e remover os resultados após o prazo definido para download.
- Tratar arquivo vazio, corrompido ou protegido com uma mensagem específica quando possível.

O tamanho máximo, o tempo de processamento e a política de retenção serão definidos após medir o motor de conversão e escolher a hospedagem. A versão pública dependerá desses limites e do isolamento dos processos.

Os limites locais atuais estão documentados no README e nos guias de cada ferramenta. QR Code usa geração em memória e não participa da fila nem da retenção de documentos.

## Arquitetura proposta

Começar com uma aplicação Python organizada por responsabilidade. Essa organização é chamada de monólito modular: os módulos fazem parte do mesmo projeto e podem evoluir separadamente.

```text
Interface no navegador
        ↓
Rotas HTTP e validação
        ↓
Serviços: documentos / PDFs / imagens / QR Code
        ↓
Motores de processamento e arquivos temporários
```

- **Interface:** aproveita o visual aprovado e implementa os fluxos de cada ferramenta.
- **Rotas:** recebem os dados e devolvem resultados ou o andamento da tarefa.
- **Serviços:** contêm as regras de cada operação, sem depender do desenho da tela.
- **Adaptadores:** controlam as bibliotecas e programas externos. Permitem trocar o motor de documentos sem reescrever os fluxos de PDF, imagem e QR Code.
- **Tarefas:** operações demoradas usam concorrência controlada e limites de execução. Antes da publicação, será necessário validar o comportamento com tarefas simultâneas.

FastAPI com templates é a proposta para a camada HTTP. A migração deve acontecer em uma etapa verificável, preservando o uso local durante a transição. O Word atual serve como referência de comparação; o candidato para o servidor público é o LibreOffice, que ainda precisa passar pela prova de conversão.

### Como funcionará na hospedagem

O visitante enviará o DOCX pelo navegador. A aplicação Python no servidor receberá o arquivo, executará o LibreOffice sem interface gráfica e disponibilizará o PDF para download. O visitante não precisará instalar Python, Word ou LibreOffice. O [modo headless e a conversão pela linha de comando](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html) são recursos documentados do LibreOffice.

Na implantação, o motor precisa estar instalado no servidor que processa os arquivos. Uma proposta é empacotar Python, a aplicação, LibreOffice e as fontes necessárias em uma imagem Docker, que reúne os arquivos e dependências de execução ([conceito de imagem Docker](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-an-image/)). Uma hospedagem Linux usará a distribuição Linux do motor; a extração Windows do laboratório serve ao desenvolvimento local.

Esse empacotamento ainda será criado. Antes de publicar, mediremos tempo e memória no servidor escolhido e definiremos a quantidade de tarefas simultâneas, a fila e a limpeza dos arquivos. As fontes disponíveis no servidor também precisam entrar na validação visual dos documentos. Quem clonar o repositório para executar o processamento na própria máquina precisará preparar essas dependências, conforme o guia do projeto.

## Ordem de desenvolvimento

1. **Prova de conversão:** comparar DOCX representativos no Word e no motor candidato, registrar diferenças e medir tempo e consumo de recursos.
2. **Base modular:** separar processamento, validação, temporários e rotas; preparar ambiente virtual e dependências reproduzíveis.
3. **Primeiro fluxo completo:** Word para PDF, com upload, processamento e download, para validar a base.
4. **Operações com PDF:** juntar PDFs e compor o fluxo de converter e juntar.
5. **Imagens e QR Code:** completar as cinco ferramentas, reaproveitando o gerador existente quando adequado.
6. **Preparação pública:** testar concorrência, limites, isolamento, limpeza dos arquivos e implantação no ambiente escolhido.

Cada etapa deve terminar com uma demonstração executável e uma explicação das decisões, para apoiar o aprendizado e a documentação do portfólio.

## Fora desta primeira versão

Cadastro, assinaturas, cobrança, histórico permanente de arquivos, QR Code dinâmico, OCR e conversão de PDF para Word. Novas ferramentas poderão entrar depois por módulos próprios.
