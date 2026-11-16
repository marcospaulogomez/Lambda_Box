# Marca, contatos e doações

A suíte agora se chama **Lambda Box**, uma criação da **Lambda Tecnologia**. A página funcional é iniciada por `Start_Suite.bat`; `Preview_Design.bat` continua abrindo a prévia histórica e não acompanha essas alterações.

## Interface

- Logo da Lambda Box no cabeçalho e símbolo próprio na aba do navegador.
- A aba inicial exibe apenas **Lambda Box**. As páginas internas identificam a ferramenta ou seção e a marca. A frase final do rodapé é **Feito para a comunidade.**
- Logo da Lambda Tecnologia no rodapé e na página de contato.
- Tema azul escuro preservado, com detalhes verdes da marca.
- Cinco cartões por linha a partir de 1.280 px; três abaixo disso, dois até 1.000 px e um até 680 px. Fontes e ícones continuam grandes, com menos largura por cartão.
- Menu e rodapé levam a `/contact` (**Crie seu sistema**) e `/support` (**Apoie o projeto**).
- Contato abre o canal escolhido pelo visitante; não há formulário coletando dados no servidor.
- Doação voluntária fica em uma página própria, sem interromper o uso das ferramentas.
- Nas ferramentas de arquivos, seleção à direita e envio à esquerda em telas acima de 900 px, com andamento no topo. Em telas menores, os painéis ficam empilhados. A lista permite arrastar para reordenar e mantém controles por teclado.

Os PNGs originais estão em `assets/branding/`. `scripts/prepare_branding.py` prepara os SVGs usados pela interface: eles incorporam os PNGs originais e enquadram as áreas visíveis. Isso remove o espaço transparente da apresentação sem redesenhar nem alterar os pixels das marcas. São contêineres SVG com imagem raster incorporada, não versões vetorizadas das logos.

```powershell
.\.venv\Scripts\python.exe scripts/prepare_branding.py
```

Substitua os PNGs em `assets/branding/` e execute esse comando para atualizar as marcas. Preserve os originais de trabalho fora dessa pasta se precisar de outras versões.

## Configuração local

Copie `.env.example` para `.env` apenas se ainda não tiver um arquivo preenchido. Instale `requirements.txt` e reinicie `Start_Suite.bat` após alterações.

| Variável | Uso público |
| --- | --- |
| `CONTACT_WHATSAPP` | Código do país, DDD e número; por exemplo, o formato é `55` seguido do número com DDD. |
| `CONTACT_EMAIL` | Link de e-mail. |
| `CONTACT_WEBSITE` | Endereço HTTPS do site. |
| `CONTACT_INSTAGRAM` | Endereço HTTPS do perfil. |
| `CONTACT_YOUTUBE` | Endereço HTTPS do canal. |
| `PIX_KEY` | Chave exibida para copiar e usada no QR Pix. |
| `PIX_RECIPIENT_NAME` | Nome do beneficiário exibido na página. |
| `PIX_RECIPIENT_CITY` | Cidade usada no QR Pix. |
| `PIX_BANK_NAME` | Instituição exibida na página, opcional. |
| `DONATION_URL` | Link HTTPS opcional de uma página de pagamento externa. |
| `PROJECT_REPOSITORY_URL` | Link HTTPS opcional do código-fonte. |
| `LIBREOFFICE_PATH` | Caminho privado do motor, sem exposição na interface. |

Campos vazios ocultam o canal correspondente. A configuração lê o `.env` da raiz, sem modificar `os.environ`; variáveis fornecidas pelo ambiente têm prioridade, inclusive valores vazios. Apenas os campos públicos selecionados são enviados aos templates. Não há rota para ler o `.env`; ele e suas variações são ignorados pelo Git, exceto o modelo vazio.

O `.env` evita que esses dados fiquem no repositório. Os canais e as instruções de doação publicados podem ser vistos por qualquer visitante e não devem ser tratados como segredos. Não coloque senhas ou tokens nesses campos. Não publique capturas de tela com contatos caso deseje mantê-los fora do histórico do Git.

## Pix

Com chave, beneficiário e cidade configurados, a página oferece QR Pix, botão de copiar chave e **Pix Copia e Cola**. O valor não é fixado: o doador escolhe no aplicativo do banco.

O adaptador em `suite/payments/pix.py` segue o [Manual BR Code](https://www.bcb.gov.br/content/estabilidadefinanceira/spb_docs/ManualBRCode.pdf) e o exemplo estático da seção 2.6.3 do [Manual de Padrões para Iniciação do Pix](https://www.bcb.gov.br/content/estabilidadefinanceira/pix/Regulamento_Pix/II_ManualdePadroesparaIniciacaodoPix.pdf). Inclui o identificador do arranjo, chave e CRC; o campo de valor é omitido. O gerador de PNG da própria suíte desenha o QR Code. A geração ocorre em memória e não consulta nem movimenta uma conta.

Nome e cidade são normalizados para caracteres ASCII e limitados a 25 e 15 caracteres no QR. A página continua mostrando o nome completo configurado. A instituição é informativa; o aplicativo bancário identifica o beneficiário pela chave cadastrada.

Sem dados suficientes para o QR, a chave configurada ainda pode ser copiada. Se nenhum meio estiver configurado, a página apresenta outras formas de apoiar, sem links de pagamento falsos. O sistema não confirma recebimento, não emite recibo e não acompanha transações.

## Cartões e Google Pay

`DONATION_URL` permite integrar depois um link de pagamento fornecido por um serviço escolhido pelo autor. A suíte apenas abre esse endereço; os meios disponíveis dependem da configuração do provedor.

Google Pay ainda não está integrado. O [fluxo oficial](https://developers.google.com/pay/api/web/overview) exige processamento do token de pagamento por um provedor, integração e acesso de produção. Essa decisão fica em uma etapa própria; não há botão simulando Google Pay nem coleta de cartão nesta versão.

## Como testar

1. Reinicie a suíte e confira nome, favicon e logos em todas as ferramentas.
2. Observe os cinco cartões na mesma linha em uma janela de pelo menos 1.280 px. Reduza a janela e confira a reorganização sem rolagem horizontal.
3. Abra **Crie seu sistema**. Confira os destinos de WhatsApp, e-mail, Instagram e YouTube que configurou. Clicar abre o canal; nenhuma mensagem é enviada automaticamente.
4. Abra **Apoie o projeto** e teste **Copiar chave Pix**. Cole em um editor para conferir.
5. Expanda **Pix Copia e Cola**, copie o código e confira a leitura pelo seu banco.
6. Leia o QR com o aplicativo bancário e confira a chave/beneficiário apresentados. Não é necessário concluir uma transferência para validar esse passo.
7. Remova temporariamente um canal do `.env`, reinicie e confirme que ele deixa de aparecer. Restaure o dado quando terminar.

Os testes automatizados comparam o BR Code com o exemplo oficial do Banco Central, incluindo CRC, e decodificam o PNG com um leitor independente. Também verificam que a rota de imagem devolve o mesmo conteúdo de Copia e Cola, que configurações ausentes não geram um código e que os arquivos de ambiente não são servidos.
