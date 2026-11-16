# Gerar QR Code

A quinta ferramenta está disponível pelo cartão **Gerar QR Code** em `Start_Suite.bat`. Aceita links ou texto, oferece uma legenda opcional abaixo do código, mostra a prévia e permite baixar `qr-code.png`.

## Como testar

Ao atualizar uma cópia existente, encerre o servidor anterior com Ctrl+C, instale as dependências e inicie novamente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\Start_Suite.bat
```

1. Abra **Gerar QR Code** na página inicial.
2. Informe um endereço completo, como `https://example.com`, e uma legenda, como `Material da aula`.
3. Clique em **Gerar QR Code**, confira a prévia e baixe o PNG.
4. Leia o PNG com a câmera de um celular. Confira se o endereço é o mesmo que você digitou.
5. Experimente uma mensagem com acentos e emojis, sem legenda. Ela deve ser recuperada como texto pelo leitor.
6. Altere o conteúdo após gerar: a prévia anterior desaparece para evitar baixar um código desatualizado. Gere novamente. **Limpar** apaga campos e resultado.

O limite é de **1.200 bytes em UTF-8**; o contador da tela ajuda a conferir. Acentos e emojis podem ocupar vários bytes. A legenda aceita até 80 caracteres em uma linha e pode exigir um texto menor se for larga demais. A fonte embutida no Pillow atende letras latinas e acentos; outros alfabetos e emojis na legenda podem aparecer sem o glifo correspondente. O conteúdo codificado aceita UTF-8, independentemente dessa fonte.

## Implementação e reaproveitamento

O gerador desktop existente foi localizado em `C:\Projetos\GERADOR_QR_CODE\app.py` e preservado. Sua lógica com a biblioteca `qrcode`, correção de erros H, margem branca de quatro módulos e legenda desenhada com Pillow foi adaptada para esta suíte. Não é necessário copiar esse projeto nem instalar CustomTkinter: a interface agora é HTML e JavaScript.

- `suite/qr/generation.py`: valida conteúdo, gera o código e compõe o PNG em memória. A legenda fica fora da área codificada. O texto original, inclusive espaços e quebras de linha, é preservado.
- `suite/services/qr_codes.py`: limita a duas gerações simultâneas por processo; uma solicitação adicional recebe HTTP 429 para tentar novamente. Essa operação curta é independente da fila de documentos.
- `suite/web/qr_routes.py`: página e `POST /api/qr-code`. Recebe JSON com `text` obrigatório e `caption` opcional; responde `image/png`, com nome fixo e `Cache-Control: no-store`.
- `suite/web/templates/qr-code.html` e `suite/web/static/qr-code.js`: formulário acessível, contador, estados de envio/erro, prévia e download. Não salvam o conteúdo no armazenamento do navegador e liberam a imagem ao substituir ou limpar o resultado.

A requisição é limitada a 16 KiB antes de interpretar o JSON, inclusive quando enviada em partes. Tipos incorretos, conteúdo vazio, Unicode inválido e excesso de capacidade produzem mensagens em português. A aplicação não consulta os links digitados.

O servidor recebe o texto e gera os bytes em memória, sem criar tarefa nem gravar conteúdo ou PNG em disco. O navegador mantém a imagem para o download até limpar, editar ou sair da página. A própria geração não precisa de Word, LibreOffice ou conexão com serviços externos. Em uma futura hospedagem, esse processamento ocorrerá no servidor; a publicação ainda depende da etapa de implantação e isolamento.

O QR Code é estático: contém o texto diretamente, sem redirecionamento da suíte e sem expiração própria. Isso não mantém um site disponível nem libera permissões de arquivos do Drive. Não há edição remota do destino após distribuir a imagem.

## Verificação automatizada

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes decodificam os PNGs com um leitor independente, `zxing-cpp`, e comparam os bytes recuperados com a entrada. Também verificam legenda, UTF-8 no limite, conteúdo inválido, requisições grandes, limite de concorrência e geração sem motor Office. O leitor é dependência de desenvolvimento, não de execução.

Com a suíte aberta, execute o teste HTTP reproduzível:

```powershell
.\.venv\Scripts\python.exe scripts/check_qr_flow.py
```

Ele gera, baixa e lê um código, verifica a rejeição de conteúdo grande e salva um exemplo fictício em `laboratory/qr-flow/qr-code.png`, ignorado pelo Git. Use `--url http://127.0.0.1:8091` se iniciou em outra porta. A leitura com celular continua recomendada para avaliar o tamanho de impressão e as condições reais de uso.

Referências das bibliotecas: [qrcode](https://pypi.org/project/qrcode/8.2/) e [zxing-cpp](https://pypi.org/project/zxing-cpp/).
