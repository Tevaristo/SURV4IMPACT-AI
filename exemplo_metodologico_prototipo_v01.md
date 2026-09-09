# Exemplo metodológico do protótipo — v01

Preparação: 2026-09-09. Referência normativa exclusiva: `criterios_v08.md`. Casos: V11; decisões: `validacao_metodologica_casos_v02.md`. O inventário V11 foi consultado para localização, versões e pendências, sem o converter em norma.

## Avaliação prévia dos candidatos

As oito aprovações são CT-01A, CT-01B, CT-01C, CT-03, CT-04A, CT-08A, CT-12A e CT-13. A validação incide no comportamento perante a entrada delimitada, não no questionário histórico nem na classificação integral de um critério. Nenhum candidato reúne cobertura aprovada dos três critérios.

| Candidato | Casos e regras com aprovação | Suficiência e limites | Decisão |
|---|---|---|---|
| D06 §8.7, parceiros Madeira 14–20, Q1–Q14, pp. 80–81 / PDF 91–92 | CT-03: D2.4-R06; CT-04A: D2.6-R01/R07 | Guião curto com introdução, perguntas, escalas e fecho. Diversidade funcional adequada; identificação não é incompatível automaticamente com confidencialidade. Uso/divulgação permanece por esclarecer. Sem comportamento aprovado D2.3. Não contém respostas de pessoas. | Não usar como original integral validado: falha a condição de independência de esclarecimentos históricos para concluir R06. |
| D09R, PO SEUR, P8/8.1–8.2.1 e contexto QA5 | CT-13: D2.3-R03 | Entrada autónoma com perguntas/opções, condição, correspondência, finalidade e TdM. Adequação localizada à adicionalidade declarada, sem ação. Não depende de obtenção documental para este resultado. Sem respostas individuais. | Candidato suficiente para uma regra; não cumpre o requisito de testar mais de uma regra aprovada nem cobre os três critérios. |
| D05 §3.2, Q11, p. 96 / PDF 4 | CT-08A: D2.4-R01/R05 | Bloco autónomo com contexto, enunciado, condição, linha e quatro colunas. Adequação da referência condicional, sem ação; não depende de esclarecimento histórico para esse resultado. Sem dados pessoais. | Satisfaz as condições para demonstrar duas regras de D2.4, mas não os três critérios. Restante instrumento não incorporado. |
| D03, IEJ, destinos/codificação | CT-01A/B/C: D2.3-R05 | Comportamentos de esclarecimento aprovados; prioridades/codificação não resolvidas. CT-01B contém inconsistência documental localizada, mas não autoriza escolher um destino ou condenar todo o percurso. | Não transpor o percurso de ex-participantes/ofertas de emprego para entidades promotoras: isso alteraria o contexto substantivo. |
| D01, população, Q08, p. 149 / PDF 22 | CT-12A: DM-02/D2.6-R08 | Suficiente para pedir unidade, formato, instruções, opções e localização; insuficiente para determinar essas respostas ou classificar D2.6. | Usar apenas a situação inicial de indeterminação; não importar D02A nem CT-12B. |

As secções B dos casos já reproduzem os inputs e os localizadores necessários. Não foi necessário reler PDFs nesta alteração; não se alega nova confirmação dos originais. Os hashes das quatro fontes, das secções B/C/D e das fichas de validação encontram-se nos metadados.

## Construção escolhida

**Questionário ilustrativo construído a partir de casos metodológicos validados.**

Cenário: entidades parceiras que também promovem projetos com apoio europeu num programa fictício. O respondente acompanha a parceria e os projetos. O âmbito de resposta distingue a entidade, o Projeto A em P5 e os projetos apoiados em P6. Programa, unidades e projeto são fictícios; não se incorporam respostas, contactos ou dados pessoais.

São 23 elementos de representação, incluindo instruções e oito perguntas curtas da mesma família de satisfação; o texto do instrumento tem cerca de 840 palavras. Não é um questionário histórico original. A montagem e as adaptações de contexto/público não foram autonomamente validadas. A duração de cinco minutos é uma previsão ilustrativa conservada da situação de origem, não uma medição desta montagem.

| Elementos | Origem | Regras | Comportamento de referência e limite |
|---|---|---|---|
| INTRO, P1, P8, FIM | CT-03 | D2.4-R06 | Ausência de incompatibilidade automática entre identificação e confidencialidade, simultaneamente com informação insuficiente sobre uso/divulgação. Pedido dirigido indispensável; apreciação integral de R06 por concluir. Não garantir anonimato/agregação nem presumir práticas inadequadas. |
| SAT, P2a–P2h, P3/P4 | CT-04A | D2.6-R01/R07 | Satisfação 1–5 e relevância/sucesso 0–100 têm funções distintas; adequação localizada sem ação. Não harmonizar automaticamente nem validar todas as propriedades das escalas. |
| P5 | CT-08A | D2.4-R01/R05 | Expectativa no projeto não concluído e execução financeira alcançada quando concluído. Adequação localizada, sem ação; a condição não se estende a outros itens. |
| P7 | CT-12A | DM-02/D2.6-R08 | Quatro enunciados sem formato/opções confirmados. Pedir unidade de resposta, formato, instruções, opções e localização na versão aplicável. Não escolher entre omissão de extração, falta documental e defeito do instrumento sem evidência. |
| APOIO, P6.1–P6.5 e contexto interno QA5/TdM | CT-13 | D2.3-R03 | Separar correspondência formal e confronto substantivo. Reconhecer avanço/configuração de projetos e cenário sem apoio, incluindo dimensão, prazo e financiamento. Adequação localizada à adicionalidade declarada, sem ação, sem prova causal nem cobertura integral da QA5. |

As correspondências e adaptações detalhadas estão em `prototipo/resources/exemplo_casos_aprovados_v01.metadata.json`. Foram substituídos nomes institucionais históricos, ajustados público/contexto e numeração, explicitados os controlos da montagem e preservados os significados das situações. Não se acrescentaram rótulos intermédios às escalas nem um campo percentual à opção que menciona «em %». Os restantes itens dos instrumentos de origem foram omitidos, conforme os metadados. Não houve anonimização de respostas: não foram incorporadas respostas reais.

## Limites da demonstração

- Há resultados positivos sem ação, esclarecimentos necessários, indeterminação da representação e impossibilidade de classificação integral com este alcance.
- Não há um resultado negativo inequívoco com correção obrigatória pré-definida. CT-04B, CT-10C e CT-11B não estão aprovados. CT-01B permite reconhecer uma inconsistência documental no seu contexto, mas não foi combinado com este público/percurso. Não se transforma a lacuna de P7 num problema demonstrado para produzir um exemplo negativo.
- P7 não contém um erro de parser artificialmente introduzido: a distinção A/B/C de DM-02 permanece aberta, como em CT-12A. A confirmação de uma representação fiel com formato desconhecido não preenche as opções em falta.
- O recurso carrega com `ambito = recorte localizado`, representação por confirmar e sem observações, pedidos, propostas ou decisões pré-carregados. A restrição de classificação é a que já existe no motor; não se criou uma regra nova.
- O motor continua a aplicar as regras dos três critérios. Apenas as sete regras acima têm expectativas localizadas de referência nesta construção; não se atribui aprovação prévia a observações sobre outros aspetos.
- As expectativas e a rastreabilidade permanecem separadas do input. Não entram no prompt normal, não substituem uma chamada real nem são mostradas como análise efetuada.

## Recurso e manutenção

O input está em `prototipo/resources/exemplo_casos_aprovados_v01.json`; a proveniência e expectativas estão no ficheiro `.metadata.json` correspondente. São lidos a partir de `Path(__file__)`, sem acesso aos casos na base de conhecimento durante o carregamento do exemplo. A dependência normativa habitual do protótipo permanece inalterada.

A antiga oficina foi preservada em `tests_prototipo/fixture_oficina.py`, exclusivamente como fixture dos testes técnicos anteriores. As expectativas e os testes semânticos de referência não foram reescritos para se adaptarem ao novo exemplo.

## Guião curto

1. Em «Instrumento e contexto», escolher «Usar questionário de exemplo» e abrir «Origem e limites do exemplo».
2. Conferir o texto bruto e os 23 elementos. Verificar SAT e as oito perguntas, a condição/grelha de P5, a justificação condicional de P6.3 e os quatro enunciados de P7 sem opções.
3. Consultar o contexto em «Instrumento e contexto». A informação de QA5/modelo lógico é contexto interno, não mensagem já comunicada ao respondente.
4. Confirmar explicitamente a representação; P7 deve continuar com formato não confirmado. Prosseguir para apreciação. Sem API configurada, a análise permanece não executada e é possível preparar relatório parcial.
5. Numa análise assistida posteriormente autorizada, confrontar apenas as situações delimitadas com os metadados. Uma resposta sobre uso/divulgação não equivale a incorporação na mensagem; uma dúvida de leitura não equivale a alteração do questionário.
6. Consultar o relatório parcial. Não existe classificação histórica integral para validar. Substituir pelo questionário do utilizador continua a limpar os dados e resultados dependentes.
