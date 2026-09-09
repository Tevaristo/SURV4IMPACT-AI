# SURV4IMPACT AI — protótipo local v01

Implementação isolada da opção B do diagnóstico técnico. O novo percurso destina-se exclusivamente a D2.3, D2.4 e D2.6. `app.py` e o motor anterior foram preservados.

## Iniciar

Na pasta desta aplicação, execute `iniciar_prototipo.bat`, ou:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app_prototipo.py --server.address 127.0.0.1 --server.port 8502
```

Abra `http://127.0.0.1:8502`. O serviço fica limitado à máquina local. Termine com Ctrl+C na consola do lançador. Se a porta estiver ocupada, termine o processo anterior ou indique outra porta no comando. O lançador da aplicação antiga continua separado.

O ambiente `.venv` atual funciona e foi preservado. As versões verificadas constam de `requirements-prototipo.txt`. Não execute o instalador antigo para iniciar o protótipo: não é necessário reinstalar o ambiente. A portabilidade do `.venv`, que herda pacotes do Python existente nesta máquina, não foi certificada noutro computador.

## API

Na verificação inicial não existia `OPENAI_API_KEY` no ambiente, em `.streamlit/secrets.toml`, nem um `.env` local. **Não foi realizada uma chamada real.** O modelo configurado por omissão é `gpt-5.6`, herdado do padrão anterior; a sua disponibilidade na conta não foi confirmada.

Pode introduzir uma chave no campo protegido da barra lateral, apenas para a sessão, ou definir `OPENAI_API_KEY` e `OPENAI_MODEL` no ambiente/ficheiro local `.streamlit/secrets.toml`. O protótipo não carrega `.env` automaticamente. Não coloque credenciais nos documentos, no relatório ou no código. `secrets.toml` e `.env` estão excluídos pelo `.gitignore`.

Execute primeiro **Testar API com conteúdo sintético**. Para guardar o diagnóstico técnico mínimo em `evidencias_prototipo/api_inicial.json`:

```powershell
.\.venv\Scripts\python.exe -m prototipo.api
```

Este comando substitui o registo técnico anterior. Só guarda sucesso/falha, modelo, latência e erro técnico sanitizado. Nunca guarda a chave. A implementação usa o padrão [Responses com saída estruturada](https://developers.openai.com/api/docs/guides/structured-outputs), validada com Pydantic, e `store=False`; não regista corpos de erro da API.

Sem chave ou com falha técnica, a extração, confirmação e relatório parcial continuam disponíveis. Não há respostas simuladas na aplicação. A análise real pode demorar: são pedidos por critério e, quando solicitadas, propostas separadas de classificação. O custo e a qualidade reais não foram medidos nesta entrega.

## Percurso

1. **Instrumento e contexto:** identificar/carregar PDF ou DOCX, ou introduzir texto fiel. Indicar versão, estado e se o conteúdo é integral ou um recorte. Substituir documento inicia uma sessão nova, sem resultados anteriores.
2. Guardar o contexto relevante, distinguindo disponibilidade e visibilidade. Não é obrigatório inventar campos desconhecidos. Identificar documentos complementares, quando existam, e conferir o seu texto após extração.
3. **Confirmar representação:** confrontar o texto bruto com o original. Editar enunciados, opções, subitens, linhas/colunas, instruções e IDs abrangidos, ordem e condições/destinos. As listas usam uma entrada por linha. É possível acrescentar/remover linhas e substituir tudo por texto fiel com localizadores. Formato não confirmado continua desconhecido.
4. Assinalar a confirmação explícita e guardar. A correção da representação mantém a versão do questionário e retira apenas verificações dependentes; acrescentar uma pergunta muda a cobertura e requer reapreciação das regras que cobrem o instrumento.
5. **Apreciação documental:** autorizar o envio dos dados confirmados e executar verificações pendentes. As observações são propostas com evidência, fonte, ação e limites; as adequações fundamentadas são conservadas. Não há pontuações nem classificações por pergunta/regra.
6. **Esclarecimentos e ações:** responder aos pedidos dirigidos ou declarar indisponibilidade/fecho expresso. Retomar as verificações dependentes. Aceitar uma proposta não a incorpora. Para registar uma alteração realizada, identificar elemento, texto, versão e localização e confirmar a incorporação; a nova representação necessita de confirmação antes da reapreciação.
7. **Decisão humana:** preparar uma proposta fundamentada por critério. Uma apreciação essencialmente incompleta permanece sem categoria. Registar categoria, responsável, fundamentação e validação expressa. Os recortes localizados não permitem classificação integral.
8. **Relatório:** visualizar e descarregar DOCX e JSON. O relatório só é concluído quando os três critérios têm proposta concluída e decisão humana atual. O JSON conserva texto bruto e histórico completo. Não há categoria global.

Todos os dados de trabalho ficam na memória da sessão. Fechar a sessão/reiniciar o servidor pode perdê-los: descarregue o relatório. Importação e retoma de sessões não estão implementadas.

## Demonstração curta

- Carregar **instrumento de demonstração**. É um questionário sintético completo sobre uma oficina, com contexto, convite, instruções, filtro, escala e resposta livre. Não contém resultados de análise pré-fabricados.
- Conferir a introdução e P1–P3, incluindo o salto para o fim e a instrução partilhada. Guardar a confirmação explícita.
- Sem API, visitar as restantes etapas e exportar o **relatório parcial**. Este percurso foi executado; exemplo em `outputs/prototipo_demo/`.
- Com API configurada e teste sintético bem-sucedido, executar a apreciação. Resolver apenas os pedidos necessários, preparar propostas e decidir humanamente cada critério. Descarregar o relatório concluído apenas se estiverem reunidas essas condições.
- Mudar a leitura de P1 e guardar: conferir o histórico e a retirada das verificações dependentes, sem registar “melhoria” do questionário. Confirmar a representação corrigida e reapreciar.

O percurso assistido completo continua por demonstrar com chamadas reais. Os testes técnicos usam respostas substitutas identificadas para exercitar contratos e formulários; essas fixtures não estão disponíveis como resultados na aplicação. Os casos localizados não validam integralmente critérios.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest tests_prototipo tests/test_parser.py tests/test_reporting.py -q
```

Para executar os oito casos aprovados e cinco provisórios com chamadas reais, após configurar a API:

```powershell
$env:PROTOTIPO_LIVE_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest tests_prototipo/test_reference_cases.py -q
```

As entradas B e expectativas C/D são lidas diretamente da V11, com hash. Os casos C/D não entram na análise normal; apenas no avaliador posterior de QA. A avaliação compara proposições e campos estruturados, aceitando paráfrases. A revisão humana dos resultados continua necessária. Sem configuração, os testes reais ficam marcados como não executados. Consultar `baseline_metodologica_prototipo_v01.md` e `evidencias_prototipo/casos_metodologicos.json`.

## Limitações conhecidas

- Chamada real, latência, qualidade/custo dos resultados e os 13 testes semânticos ainda não verificados por falta de credenciais.
- Sem OCR. O parser conserva texto extraível e candidatos, mas matrizes/associações/saltos podem exigir correção ou transcrição textual. Não assume resposta aberta por falta de opções.
- A validade semântica das observações, o alcance das dependências declaradas e a materialidade exigem revisão humana. Os guardas de esquema/evidência não constituem certificação metodológica.
- Foram testados o arranque real, o health endpoint e a interface por AppTest. A inspeção visual em largura normal/reduzida permanece pendente: não havia navegador disponível no controlo de interface. As regras responsivas e a ordem dos logótipos foram verificadas no código/testes.
- DOCX gerado e conferido estruturalmente. A renderização visual foi tentada mas o LibreOffice/`soffice` não está instalado. Não foi declarada aprovação visual do documento.
- Sem Git disponível: sem commit inicial. Manifesto de integridade preserva rastreabilidade dos ficheiros anteriores monitorizados.
- Fora desta versão: Excel, importação/retoma de sessões, OCR, ensaios empíricos/digitais e correção da navegação antiga. Os quatro insucessos de navegação antigos foram reproduzidos e conservados.

## Ficheiros

- Entrada e arranque: `app_prototipo.py`, `iniciar_prototipo.bat`.
- Módulos novos: `prototipo/models.py`, `norma.py`, `extraction.py`, `state.py`, `api.py`, `engine.py`, `ui.py`, `reporting.py`, `demo.py`, `verify_delivery.py` e `__init__.py`.
- QA: `tests_prototipo/`, `evidencias_prototipo/`; exemplos gerados em `outputs/prototipo_demo/`.
- Documentação: esta página, `baseline_metodologica_prototipo_v01.md`, `entrega_prototipo_v01.md`, `requirements-prototipo.txt`.
- Único ficheiro anterior alterado: `.gitignore`. Aplicação antiga, parser, exportador antigo, testes anteriores, assets e fontes metodológicas preservados.
