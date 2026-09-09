# SURV4IMPACT AI — Assistente de Revisão Metodológica de Questionários

Versão 2.0 da prova de conceito em português para rever questionários segundo um subconjunto prioritário do Domínio 2 do quadro analítico SURV4IMPACT. A aplicação aceita questionários em Word (`.docx`) e PDF (`.pdf`).

O produto implementa o fluxo selecionado para a experiência da aplicação:

1. carregar e contextualizar um DOCX ou PDF;
2. confirmar a estrutura extraída;
3. rever constatações explicáveis;
4. validar a síntese metodológica;
5. exportar relatório Word, grelha Excel ou dados JSON.

## Princípios metodológicos

- A matriz de conhecimento é a fonte das regras e da terminologia.
- Constatação e síntese são níveis separados.
- Critérios relacionados são apresentados como ligações, evitando dupla contagem.
- A revisão de IA é opcional e produz apenas propostas.
- A classificação final requer decisão pericial.
- Não é calculada uma pontuação de qualidade não validada pelo quadro.

## Formatos de entrada

- **DOCX:** são analisados parágrafos e tabelas que contenham texto editável.
- **PDF:** são analisados documentos digitais que contenham uma camada de texto selecionável. O extrator preserva, tanto quanto possível, a sequência das páginas, perguntas, opções e elementos tabulares.

Antes de carregar um PDF, confirme que consegue selecionar e copiar texto no leitor de PDF. Um documento digitalizado pode ter aparência normal, mas ser apenas uma coleção de imagens.

A versão 2.0 **não executa OCR**. Por isso, PDFs digitalizados ou compostos apenas por imagens não podem ser analisados. Nesses casos, aplique primeiro OCR numa ferramenta apropriada ou disponibilize uma versão DOCX/PDF com texto selecionável.

Independentemente do formato, a etapa **Questionário interpretado** permite confirmar e corrigir a estrutura extraída antes da revisão metodológica.

## Executar no Windows

### Opção simples

1. Instale Python 3.14 de 64 bits e selecione **Add Python to PATH** durante a instalação.
2. Execute por duplo clique `instalar_aplicacao.bat`.
3. Depois da instalação, execute `iniciar_aplicacao.bat`.

O instalador cria um ambiente privado na pasta `.venv`; não altera outros projetos Python no computador.
Se encontrar um ambiente criado durante o desenvolvimento e perguntar se pretende recriá-lo, responda `s`.

A aplicação foi executada e testada em Python 3.12. A resolução integral das dependências para CPython 3.14/Windows 64 bits também foi verificada antes da entrega.

### Instalação manual

Com Python 3.11 ou mais recente instalado:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

A aplicação abre normalmente em `http://localhost:8501`.

Depois da instalação, também pode iniciar por duplo clique em `iniciar_aplicacao.bat`. A janela que aparece mantém o serviço local ativo; para terminar, feche essa janela.

Se não tiver Python instalado, consulte primeiro a secção **Instalação simplificada** abaixo.

## Revisão de IA opcional

A aplicação funciona sem API, usando as regras locais. Para a revisão semântica:

1. ative **Configuração da IA** na barra lateral;
2. introduza uma chave na sessão, ou defina `OPENAI_API_KEY` no ambiente;
3. confirme o modelo no campo configurável;
4. carregue um DOCX ou PDF e analise novamente o questionário.

O texto estruturado das perguntas e o contexto necessário são enviados à API apenas quando a opção está ativa. A integração usa a Responses API com saída estruturada segundo modelos Pydantic.

## Estrutura

```text
app.py                         interface Streamlit
assets/styles.css              identidade e componentes visuais
assets/brand/                  logótipos institucionais e de cofinanciamento
surv4impact/parser.py          extração e normalização de DOCX/PDF
surv4impact/rules.py           regras determinísticas e híbridas
surv4impact/ai.py              revisão semântica opcional
surv4impact/synthesis.py       lógica de síntese D2.1.03
surv4impact/reporting.py       Word, Excel e JSON
work/matrix_build/*.json       base de conhecimento da matriz
tests/                         testes automatizados
```

## Limitações conhecidas da v2.0

- O PDF tem de conter texto selecionável. Não existe OCR integrado; PDFs digitalizados ou compostos apenas por imagens não são suportados.
- Por segurança e desempenho, cada PDF está limitado a 50 MB e 300 páginas.
- A ordem de leitura de PDFs com várias colunas, caixas posicionadas, cabeçalhos repetidos ou composição gráfica complexa pode não coincidir integralmente com a ordem visual.
- Grelhas e tabelas complexas em PDF podem exigir correção manual na etapa de confirmação da extração.
- Em DOCX, caixas de texto, imagens e elementos gráficos complexos podem não ser extraídos.
- A validação visual de responsividade e associação entre controlos e rótulos requer evidência adicional.
- Os limiares de triagem devem ser calibrados com questionários já avaliados.
- Não existe autenticação nem armazenamento persistente multiutilizador.

## Instalação simplificada

Para uma entrega posterior no Toolbox, o projeto pode ser publicado online ou empacotado com um lançador/instalador. A versão 2.0 mantém o código modular para permitir ambos os percursos sem alterar a matriz.
