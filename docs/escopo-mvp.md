# Primeira versão da suíte

## Prioridade e estado atual

A prioridade é construir o software. Nome, logo, favicon, ícones próprios e animações serão retomados depois. A aparência azul aprovada é a base provisória da interface.

MVP significa primeira versão utilizável: um conjunto limitado de ferramentas com resultados verificáveis e um fluxo completo de entrada, processamento e download.

Hoje existem duas partes distintas:

- **Aplicativo funcional:** `app.py` e `public/`, iniciados por `Iniciar_Conversor.bat`. Automatiza o Word instalado no Windows e oferece o fluxo de converter e juntar. A junção normalmente usa PDF-Lib no navegador.
- **Prévia da suíte:** `outputs/previa-suite-autoral.html`, exportada para `outputs/testar-visual.html` e aberta por `Testar_Visual.bat`. Exibe as cinco ferramentas, mas ainda não realiza operações com arquivos.

Este documento define o que será implementado; não declara que a suíte funcional já está pronta.

## Ferramentas e critérios de conclusão

| Ferramenta | Entrada inicial proposta | Resultado esperado | Verificação principal |
| --- | --- | --- | --- |
| Word para PDF | Um ou mais DOCX | PDF individual por documento; ZIP para download em lote | Abrir os PDFs e comparar paginação, tabelas, imagens e fontes com os originais |
| Juntar PDFs | Dois ou mais PDFs | Um PDF com as páginas na ordem definida | Conferir ordem, número de páginas e dimensões das páginas |
| Converter e juntar | DOCX e PDFs existentes | Um PDF final respeitando a ordem dos arquivos | Conferir a posição de cada documento e a preservação das páginas dos PDFs enviados |
| Imagens para PDF | JPG e PNG | Um PDF com as imagens na ordem escolhida | Conferir proporções, orientação e ordem, sem cortar a imagem por acidente |
| QR Code | Link ou texto | QR Code estático para baixar em PNG | Ler o código no celular e conferir o conteúdo recuperado |

DOCX é a proposta inicial para reduzir a matriz de validação. O conversor atual aceita outros formatos; o suporte deles na nova suíte será decidido com testes, sem retirar recursos do aplicativo atual nesta etapa.

O gerador de QR Code existente ainda precisa ser localizado e avaliado para reaproveitamento. Um QR Code estático armazena diretamente o conteúdo e dispensa um serviço de redirecionamento próprio.

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
