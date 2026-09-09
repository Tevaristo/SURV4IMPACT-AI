# Entrega técnica — protótipo SURV4IMPACT AI v01

Data: 2026-09-09. Opção B implementada em entrada e módulos separados. O percurso local está funcional; **a qualificação metodológica com respostas reais e a demonstração assistida integral permanecem pendentes de configuração da API**. Não se apresenta esta entrega como aprovação metodológica integral.

## Implementado

- Entrada `app_prototipo.py` e lançador próprio, usando a `.venv` existente.
- Navegação por `intake`, `structure`, `review`, `clarifications`, `decisions`, `report`, com validação antes de guardar destinos.
- Cabeçalho institucional com os três ficheiros originais de `assets/brand`, na ordem anterior e sem alterar imagens; adaptação responsiva no código.
- Contexto, disponibilidade e visibilidade; documentos complementares opcionais com confirmação do texto.
- Leitura PDF/DOCX reutilizada, texto bruto/localizadores, candidatos com formato desconhecido e representação editável/confirmável, incluindo matrizes, instruções partilhadas e saltos.
- Carregamento direto da V08 com versão/hash; apenas três critérios e DM-01 a DM-05 nos prompts pertinentes.
- Motor novo com saída estruturada, evidência textual verificável, resultados positivos, pedidos dirigidos e estados distintos; sem motor/catálogo antigo, contagens ou pontuações.
- Invalidação por dependências, incluindo instruções partilhadas, mudanças de cobertura, contexto/documentos e pedidos. As observações e ações retiradas ficam no histórico.
- Propostas classificativas separadas da decisão humana expressa; uma categoria por critério e nenhuma categoria global.
- Aceitação de propostas separada da confirmação de incorporação em versão revista; correções da representação conservam a versão do questionário.
- Relatório visualizável, DOCX e JSON, parcial/concluído, com proveniência, observações, pedidos/respostas, ações, limites e decisão humana.

## Ficheiros criados e alterados

| Grupo | Ficheiros |
|---|---|
| Entrada/arranque | `app_prototipo.py`, `iniciar_prototipo.bat` |
| Núcleo novo | `prototipo/__init__.py`, `models.py`, `norma.py`, `state.py`, `extraction.py`, `api.py`, `engine.py`, `reporting.py`, `ui.py`, `demo.py` |
| Verificação de entrega | `prototipo/verify_delivery.py` |
| Testes novos | `tests_prototipo/__init__.py`, `conftest.py`, `test_workflow.py`, `test_app.py`, `cases.py`, `test_reference_cases.py` |
| Documentação/requisitos | `README_PROTOTIPO.md`, `baseline_metodologica_prototipo_v01.md`, `requirements-prototipo.txt`, este documento |
| Evidências | `evidencias_prototipo/integridade_inicial.json`, `preservacao_final.json`, `api_inicial.json`, `pytest.xml`, `navegacao_antiga.xml`, `casos_metodologicos.json`, `demonstracao_local.json`, `arranque_real.json`, `qa_visual.json` |
| Exemplos gerados, excluídos de Git | `outputs/prototipo_demo/relatorio_parcial_demo.docx` e `.json` |
| Ficheiro anterior alterado | Apenas `.gitignore`, reforçado para credenciais, ambiente, caches, logs, uploads, temporários e outputs |

Preservados `app.py`, frontend e motor antigos, parser e exportador antigos, testes anteriores, questionários, metodologia, evidências e imagens. **85 ficheiros preexistentes monitorizados foram conferidos por SHA-256, sem alterações ou desaparecimentos.** O manifesto cobre os ficheiros relevantes selecionados, não todo o ambiente/dependências/caches. `.gitignore` foi a alteração autorizada fora desse manifesto.

Git não disponível no PATH nem nos caminhos usuais verificados: **não foi criado commit inicial**. Prosseguiu-se nos termos autorizados, com a cópia de segurança externa declarada. `.venv` não foi eliminada, recriada ou atualizada.

## Arranque

Abrir `iniciar_prototipo.bat` na pasta da aplicação, ou executar nessa pasta:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app_prototipo.py --server.address 127.0.0.1 --server.port 8502
```

Endereço: `http://127.0.0.1:8502`. O servidor de verificação iniciou e devolveu `ok` no health endpoint. O comando e lançador utilizam exclusivamente o novo ponto de entrada.

## Resultados dos testes

| Bateria/verificação | Resultado | Alcance |
|---|---|---|
| `tests_prototipo` + parser/exportação anteriores | **71 passados, 13 não executados**, em 32,64 s na última execução | Inclui arranque e seis páginas, PDF/DOCX, substituição, estado novo, desconhecido, grelha, instruções/saltos, invalidação, API em falha, pedidos/fecho, decisão humana e exportação |
| Parser e exportação anteriores incluídos acima | 21 passados | Regressão dos mecanismos reutilizados |
| Navegação da aplicação antiga, execução separada | **3 passados, 4 falhados** | Mesma inconsistência de nomes já diagnosticada; não corrigida nem ocultada |
| Preservação | 85 hashes conferidos; zero alterações/desaparecimentos no manifesto | Fontes e documentos monitorizados |
| Servidor real | Arranque em loopback e health `ok` | Não substitui ensaio visual/end-to-end com API |
| Interface em largura normal/reduzida | Verificações de código/ordem/proporções responsivas; inspeção visual por concluir | Não havia navegador disponível, incluindo tentativa do navegador integrado |
| DOCX | Bytes/ZIP, conteúdo, imagens e estrutura verificados | Renderização tentada; `soffice`/LibreOffice inexistente; QA visual não concluído |

As fixtures técnicas são expressamente identificadas nos testes e não existem como respostas na aplicação. A passagem dos testes técnicos não prova a correção metodológica de futuras respostas do modelo.

## API e casos metodológicos

Não foi encontrada chave no ambiente, em `secrets.toml` ou num `.env` local. **Chamada real: não realizada.** Modelo configurado: `gpt-5.6`; modelo efetivamente utilizado: nenhum; latência: não medida. O registo técnico não contém credenciais. Configurar uma chave com acesso ao modelo pretendido e executar o teste sintético descrito no README.

| Estatuto | Casos | Execução nesta sessão |
|---|---|---|
| Oito referências aprovadas obrigatórias | CT-01A, CT-01B, CT-01C, CT-03, CT-04A, CT-08A, CT-12A, CT-13 | Corpus B e expectativas C/D carregados e conferidos; **execução semântica real não realizada** |
| Cinco provisórios coerentes, sem aprovação da responsável | CT-02, CT-04B, CT-10A, CT-10C, CT-12B | Corpus/estatutos conferidos; **execução semântica real não realizada** |
| Restantes casos exploratórios | CT-05, CT-06, CT-07, CT-08B, CT-09, CT-11A, CT-11B, CT-11C | Não executados; não bloqueiam esta entrega |

As expectativas são extraídas dos documentos originais, sem alteração. A bateria live chama o motor e compara proposições/ação/estado/limites por avaliador de QA em separado, aceitando paráfrases e produzindo artefactos para revisão humana. O input da análise é só B do próprio caso; C/D não entram no prompt normal. A qualificação dos oito aprovados continua obrigatória e pendente. Casos localizados não validam automaticamente classificações integrais.

## Demonstração e limites

Foi executado o percurso local com um instrumento sintético completo sobre uma oficina: contexto suficiente, convite, instrução partilhada, filtro, escala, resposta livre, representação confirmada, navegação nas seis etapas e exportação parcial real. Não houve análise da API nem decisão humana metodológica efetiva nesta demonstração. Os formulários de pedidos e decisão foram adicionalmente exercitados por testes técnicos com fixtures identificadas.

Guião curto:

1. Iniciar o protótipo e escolher **Carregar instrumento de demonstração**.
2. Conferir introdução/P1–P3 e confirmar explicitamente a representação.
3. Sem chave, observar o estado técnico e exportar relatório parcial.
4. Com chave validada, executar verificações, responder apenas aos pedidos necessários e reapreciar dependências.
5. Preparar propostas por critério; registar responsável, fundamentação e validação humana expressa; descarregar DOCX/JSON.
6. Corrigir a leitura de um elemento e conferir a retirada das verificações dependentes. Aceitação de uma proposta não deve aparecer como alteração incorporada.

Limitações: não há OCR; estruturas complexas podem precisar de transcrição manual; sem chamada real não estão certificados modelo, custos, latência ou qualidade. A validação de citações/esquema não comprova toda a interpretação semântica; alcance das dependências e materialidade exigem revisão humana. Sessões são temporárias, sem importação/retoma. O DOCX não tem aprovação visual; a interface também necessita de inspeção visual em duas larguras.

## Tempo e gates

Estimativas aproximadas de tempo decorrido nesta sessão, arredondadas e sem cronómetro por bloco; **cerca de 0,8 horas**, não 30 horas consumidas:

| Bloco | Estimativa |
|---|---:|
| Leitura, preservação e diagnóstico inicial de API | 0,15 h |
| Entrada, identidade, contexto e representação | 0,15 h |
| Motor, estados, dependências e esclarecimentos | 0,15 h |
| Decisão humana e relatório | 0,10 h |
| Testes, demonstração local e robustez | 0,15 h |
| Documentação de entrega e limitações | 0,10 h |

O arranque, identidade no AppTest e estado da API ficaram conhecidos antes do gate de 2 h. As funcionalidades locais foram implementadas dentro dos limites temporais pedidos. Os gates de análise/demonstração assistida real e QA visual **não são declarados concluídos**: dependem das condições externas acima, não de tempo adicional de implementação. Não foram retirados confirmação, fecho, decisão humana, relatório ou identidade para reduzir tempo.

Ficaram fora: Excel, importação/retoma, OCR, aperfeiçoamentos visuais adicionais, ensaios empíricos/programados e correção da navegação antiga. Nenhuma decisão metodológica adicional foi inventada.
