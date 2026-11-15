# Direção visual da suíte

Este documento registra a proposta em avaliação. O nome e a marca ainda serão definidos pelo autor do projeto. A identidade visual está adiada: a prioridade atual é construir e validar as ferramentas.

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
- Cartões compactos, com altura mínima de 264 px e cantos de 5 px. O conteúdo pode aumentar a altura quando necessário; o formato quadrado não é obrigatório.
- Ícones de 52 px, títulos de 26 px e descrições de 15 px na configuração inicial.
- IBM Plex Sans para textos e títulos; IBM Plex Mono para indicações curtas de formato. A prévia carrega essas fontes pela internet e possui fontes alternativas do sistema.
- Ícones de uma única família, com espessura e tamanho consistentes. Cores discretas identificam documentos, PDFs, imagens e QR Code.
- Tipografia e alinhamento como elementos principais da composição.
- Texto direto sobre a tarefa de cada ferramenta.
- Estados de foco visíveis e navegação por teclado.
- Grade com três colunas em telas amplas, duas em telas intermediárias e uma em celulares.

Os valores de tamanho são pontos de partida para avaliação visual. A definição final deve considerar textos longos, celulares e ampliação do navegador.

## Nome, logo e favicon

Etapa adiada pelo autor. A marca provisória permite continuar o desenvolvimento funcional.

O favicon é o ícone exibido na aba do navegador. Convém derivá-lo de um símbolo simples da marca, legível em 16 × 16 e 32 × 32 px.

Ao desenvolver a marca fora do projeto, preparar:

1. Nome e sua grafia oficial.
2. Logo principal em SVG, com fundo transparente.
3. Símbolo separado do nome, também em SVG.
4. Variações para fundos claros e escuros.
5. Cores de referência e nomes das fontes utilizadas, com suas condições de uso.

Após escolher a marca, integrar o cabeçalho, o favicon, os ícones de instalação quando aplicáveis e a apresentação do repositório. A palavra “Suíte” é apenas um identificador provisório da prévia.

## Melhorias visuais registradas para depois

- Aproveitar melhor a largura e a altura da página para reduzir a rolagem.
- Reduzir a largura e a altura dos cartões da grade, hoje considerados grandes pelo autor, preservando a legibilidade dos textos e ícones. Avaliar mais cartões por linha em telas amplas.
- Na tela de Word para PDF, avaliar o progresso no topo e a lista de arquivos ao lado da área de trabalho.
- Validar essa composição também no celular, mantendo os estados e os controles acessíveis.
- Receber e integrar os ícones específicos que serão criados pelo autor.
- Experimentar uma animação breve no ícone ao passar o mouse, como aumentar e retornar à escala original.
- Definir também o comportamento com foco pelo teclado e respeitar a preferência por movimento reduzido.
- Avaliar transições de CSS para a animação; usar JavaScript quando a interação precisar de estado ou coordenação adicional.

Essas animações ainda não foram implementadas. Os tamanhos das fontes aprovados devem ser preservados durante os ajustes de espaçamento.

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
