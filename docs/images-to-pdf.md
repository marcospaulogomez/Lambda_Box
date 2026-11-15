# Imagens para PDF

A ferramenta está disponível pelo cartão **Imagens para PDF**, em `/images-to-pdf`, e pela API `POST /api/jobs/images-to-pdf`. Ela usa Pillow para ler e normalizar as imagens e ReportLab para montar o PDF. Não depende de Word ou LibreOffice.

## Comportamento desta versão

- Aceita de 1 a 10 arquivos JPG, JPEG ou PNG estáticos, de até 8 bits por canal.
- Cria um PDF único, com uma imagem por página, respeitando a ordem escolhida nos botões ↑ e ↓.
- Usa páginas A4, em paisagem quando a imagem é mais larga que alta e em retrato nos demais casos.
- Centraliza a imagem com margem mínima de 12 mm, ajustando a exibição proporcionalmente, sem cortes ou redução da resolução em pixels.
- Corrige a orientação EXIF antes de escolher a orientação da página. A [operação `exif_transpose` do Pillow](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html#PIL.ImageOps.exif_transpose) aplica rotações e espelhamentos registrados pela câmera.
- Converte para RGB e compõe transparências sobre branco, incluindo PNG com paleta e transparência.
- Disponibiliza `images.pdf`, com a quantidade de páginas informada no resultado da tarefa.

O uso de [`drawImage` do ReportLab](https://docs.reportlab.com/reportlab/userguide/ch2_graphics/#image-methods) mantém as imagens incorporadas no PDF. A conversão usa os pixels decodificados em RGB; o resultado pode ser maior que um JPEG original. Perfis de cor para impressão e preservação de metadados de câmera não fazem parte desta versão.

## Limites e validação

Continuam valendo 20 MB por arquivo, 50 MB por tarefa, fila compartilhada de até quatro tarefas ativas e processamento de uma tarefa por vez. Os resultados expiram após 30 minutos e podem ser excluídos pelo usuário antes disso.

Além dos bytes, há limites iniciais de **40 milhões de pixels por imagem** e **100 milhões de pixels por tarefa**, configurados em `Settings.max_image_pixels` e `Settings.max_total_image_pixels`. Uma imagem comprimida pequena pode exigir muita memória ao ser decodificada; a [documentação do Pillow](https://pillow.readthedocs.io/en/stable/reference/Image.html) descreve essa diferença e sua proteção para imagens com dimensões excessivas.

O serviço verifica o conteúdo real e sua correspondência com a extensão, decodifica os pixels para detectar dados incompletos e rejeita imagens animadas, profundidade de cor não suportada e formatos diferentes dos aceitos. HEIC, GIF, WebP, TIFF e SVG não são aceitos nesta etapa. Nenhuma página parcial é disponibilizada se um arquivo falhar.

As imagens originais não são modificadas. As cópias de upload e os temporários de geração são removidos ao terminar; o PDF final segue a mesma política de retenção das outras ferramentas. O processamento de imagens ainda roda no processo local, sem isolamento ou encerramento forçado por tarefa. A preparação para arquivos públicos e a medição de memória permanecem pendentes.

## Testar pelo navegador

1. Se o servidor já estiver aberto, encerre-o com Ctrl+C. Atualize as dependências e inicie novamente:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\Start_Suite.bat
   ```

2. Clique em **Imagens para PDF**, selecione uma ou mais imagens e ajuste a ordem.
3. Clique em **Gerar PDF** e baixe o resultado. Confira uma imagem por página, orientação, proporção e transparência sobre branco.
4. Atualize a aba e confira a recuperação do resultado. Use **Excluir arquivos desta tarefa** e verifique que o download deixa de funcionar.

## Teste HTTP reproduzível

Com o servidor local aberto e as dependências de desenvolvimento instaladas:

```powershell
.\.venv\Scripts\python.exe scripts/check_image_flow.py
```

O script gera uma imagem em cinza, uma foto JPEG com orientação EXIF e um PNG transparente. Ele envia os arquivos pela API, confere as três páginas, a ordem, a orientação, os pixels incorporados e a exclusão. Também verifica rejeição de arquivo inválido e integridade dos originais. As evidências e o PDF ficam em uma pasta nova de `laboratory/image-flow/`, ignorada pelo Git. Para outra porta, use `--url http://127.0.0.1:8091`.

Na execução de 15/11/2026 em um servidor sem LibreOffice, os três arquivos geraram três páginas em 0,082 segundo de processamento e 0,768 segundo entre o início do upload e a confirmação de conclusão. As verificações de ordem, orientação, transparência, exclusão e originais passaram. Evidências locais: `laboratory/image-flow/54b20a63/report.json`. Os tempos são dessa pequena amostra local; não estimam a capacidade de hospedagem.

Os 52 testes automatizados passaram, incluindo as ferramentas anteriores. Os testes de imagens examinam também margens, centralização, proporção, rotação EXIF, transparência de paleta, escala de cinza, CMYK, limites de pixels e falhas sem publicação parcial.

A conferência no Chrome, usando o mesmo servidor sem LibreOffice, também passou: acesso pelo cartão, seleção de uma imagem, rejeição de formato não aceito, reordenação de três imagens, download na ordem escolhida, recuperação após atualizar a aba e exclusão. A tela foi conferida em largura de 390 px, sem rolagem horizontal, e não foram capturadas exceções JavaScript. Evidências locais: `laboratory/preview-suite/image-ui-report.json` e capturas nessa mesma pasta.
