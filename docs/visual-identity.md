# Direção visual da suíte

Este documento registra a direção visual da **Lambda Box**, criada pela **Lambda Tecnologia**. Após concluir os cinco fluxos locais, o autor retomou a identidade visual e forneceu as logos e o símbolo para a aba do navegador. Consulte [marca, contatos e doações](branding-and-contact.md) para configuração e testes.

## Objetivo

Construir uma suíte com identidade própria, fácil de reconhecer e de usar. O projeto combina aprendizado pessoal, portfólio no GitHub e a intenção de atender à comunidade.

## Decisões já aceitas

- Tema azul escuro nativo.
- Página inicial organizada em grade de ferramentas.
- Cinco ferramentas iniciais: Word para PDF, juntar PDFs, converter e juntar, imagens para PDF e QR Code.
- Ícones e textos com presença suficiente para ocupar os cartões de forma equilibrada.
- Python como base de processamento. A identidade visual independe do framework escolhido.

## Proposta em avaliação

- Fundo azul profundo e cartões com contraste moderado.
- Cartões compactos, com altura mínima de 248 px e cantos de 5 px. O conteúdo pode aumentar a altura quando necessário; o formato quadrado não é obrigatório.
- Ícones de 52 px, títulos de 26 px e descrições de 15 px na configuração inicial.
- IBM Plex Sans para textos e títulos; IBM Plex Mono para indicações curtas de formato. A prévia carrega essas fontes pela internet e possui fontes alternativas do sistema.
- Ícones de uma única família, com espessura e tamanho consistentes. Cores discretas identificam documentos, PDFs, imagens e QR Code.
- Tipografia e alinhamento como elementos principais da composição.
- Texto direto sobre a tarefa de cada ferramenta.
- Estados de foco visíveis e navegação por teclado.
- O botão **Apoie o projeto** tem fundo verde da marca e texto escuro, inclusive quando a página de apoio está selecionada.
- Os ícones das ferramentas fazem um movimento breve de subida, aumento e inclinação ao passar o mouse ou receber foco pelo teclado. A animação termina em 420 ms, sem repetição contínua, e é desativada quando o visitante prefere movimento reduzido.
- Nas ferramentas de arquivos, envio à esquerda e lista à direita em telas acima de 900 px. Em telas menores, os painéis ficam empilhados.
- Andamento acima dos painéis. A lista de seleção tem rolagem própria e permite arrastar arquivos, com setas como alternativa por teclado.
- Grade com cinco colunas a partir de 1.280 px, três abaixo desse limite, duas até 1.000 px e uma até 680 px.

Os valores de tamanho são pontos de partida para avaliação visual. A definição final deve considerar textos longos, celulares e ampliação do navegador.

## Nome, logo e favicon

Nome oficial: **Lambda Box**. A logo principal aparece no cabeçalho, o símbolo é usado no favicon e a marca **Lambda Tecnologia** identifica o autor no rodapé e na página de contato. Os arquivos fornecidos foram preservados em `assets/branding/`.

O favicon é o ícone exibido na aba do navegador. Convém derivá-lo de um símbolo simples da marca, legível em 16 × 16 e 32 × 32 px.

Ao desenvolver a marca fora do projeto, preparar:

1. Nome e sua grafia oficial.
2. Logo principal em SVG, com fundo transparente.
3. Símbolo separado do nome, também em SVG.
4. Variações para fundos claros e escuros.
5. Cores de referência e nomes das fontes utilizadas, com suas condições de uso.

Cabeçalho, favicon, rodapé e título do aplicativo funcional já usam a nova marca. A prévia histórica em `outputs/` continua com a identidade provisória. Ícones de instalação e novos formatos de marca podem ser avaliados depois.

## Melhorias visuais registradas para depois

- Aproveitar melhor a largura e a altura da página para reduzir a rolagem.
- Os cartões da página funcional já foram estreitados, com cinco ferramentas por linha em telas amplas. Continuar avaliando a legibilidade em futuras ferramentas.
- Progresso no topo e lista lateral já foram aplicados às quatro ferramentas de arquivos, com composição empilhada no celular.
- Receber e integrar os ícones específicos que serão criados pelo autor.
As animações atuais são feitas em CSS, sem dependência adicional de JavaScript. Os tamanhos das fontes aprovados devem ser preservados durante os ajustes de espaçamento.

## Como avaliar a prévia

Executar `Preview_Design.bat` na raiz do projeto. O arquivo abre a versão atual exportada em `outputs/design-preview.html`.

- Observar o equilíbrio entre ícone, título, descrição e espaço do cartão.
- Avaliar os destaques ao passar o mouse e selecionar uma ferramenta.
- Navegar com Tab e ativar cartões com Enter ou Espaço.
- Reduzir a janela para conferir a reorganização da grade.
- Ampliar o navegador para 200% e conferir a leitura e os controles.

A prévia não faz conversões. O aplicativo funcional continua disponível em `Start_Converter.bat`.

## Portfólio

Além da identidade visual, a apresentação do projeto deve incluir instruções reproduzíveis, capturas de tela, decisões de arquitetura, testes relevantes e limitações conhecidas da conversão. Esses itens serão construídos nas próximas etapas; este documento não declara que já foram implementados.
