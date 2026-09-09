# Baseline metodológica do protótipo — v01

Data: 2026-09-09. Âmbito exclusivo: apreciação do desenho documental de D2.3, D2.4 e D2.6. Esta baseline regista fontes, estatutos e limites de implementação; não constitui uma norma paralela.

## Fonte normativa

`../base de conhecimento SURV4IMPACT ai REVIEW TOOL/criterios_v08.md`, versão v08.

SHA-256 conferido: `851e0e7cb4e8d583bce856f67e6e33827fca88e34ce8609bea32ff042bb2c26f`.

O carregador lê as três fichas até à secção 10, os significados da escala e as decisões DM-01 a DM-05. Não transporta para a análise os exemplos históricos, a bibliografia final, inventários, versões anteriores ou os documentos de casos de teste. Por chamada, envia o enquadramento do critério, as regras ainda sem resultado atual e as decisões transversais pertinentes. A síntese recebe a ficha do respetivo critério. O ficheiro normativo não foi alterado.

Aplicam-se os estatutos [E/D/O/V] da V08. Um juízo contextual não é uma decisão geral em falta. Uma opção metodológica não coberta fica registada em `pendencia_metodologica`, sem solução inventada. Não foram adotadas decisões metodológicas adicionais.

## Testes e estatutos

Fontes de QA: `casos_teste_metodologicos_v11.md` e `validacao_metodologica_casos_v02.md`, na pasta `casos_teste` da base de conhecimento. Os comportamentos aprovados são decisões de Teresa Evaristo de 2026-09-08, com o alcance delimitado na consolidação V02. Não aprovam os questionários históricos, não resolvem intenções em falta e não validam classificações integrais.

| Estatuto nesta entrega | Casos |
|---|---|
| Referências obrigatórias aprovadas | CT-01A, CT-01B, CT-01C, CT-03, CT-04A, CT-08A, CT-12A, CT-13 |
| Provisórios coerentes; não aprovados pela responsável | CT-02, CT-04B, CT-10A, CT-10C, CT-12B |
| Exploratórios; não bloqueiam esta entrega | CT-05, CT-06, CT-07, CT-08B, CT-09, CT-11A, CT-11B, CT-11C |

CT-02, CT-04B, CT-10A e CT-12B foram reformulados e aguardam revalidação; CT-10C é novo e está por validar. O qualificador “provisório coerente” não substitui esses estatutos de origem.

`inventario_documentos_teste_v11.md` é exclusivamente um índice de localização e rastreabilidade. Não fornece regras ou respostas ao modelo. A entrada da análise de cada caso é exclusivamente a secção B do próprio caso; C/D só entram na avaliação posterior de QA, em separado. As expectativas são extraídas do ficheiro original, sem as reescrever para acomodar respostas.

## Condições de aceitação e limitações

- Os testes técnicos usam fixtures claramente identificadas para verificar contratos, estados, invalidação e exportação. Não são resultados reais de IA nem validação metodológica.
- Os testes semânticos reais dos oito casos aprovados são um gate obrigatório de qualificação. Os cinco provisórios devem também ser executados mantendo o estatuto. Sem credenciais, são registados como **não executados**, nunca como passados.
- A avaliação automática de QA compara proposições, ação, estado e limites; aceita paráfrases. Os artefactos incluem todas as respostas e justificações para revisão humana. Um avaliador automático pode falhar e não representa a aprovação da responsável.
- Os casos localizados não permitem classificar integralmente D2.3, D2.4 ou D2.6. A aplicação bloqueia propostas classificativas para sessões marcadas como recorte localizado.
- Uma representação confirmada pode conter formatos declarados desconhecidos: isso não os transforma em respostas livres. As verificações dependentes seguem DM-02; as independentes podem continuar.
- Falhas de API permanecem estados técnicos. Sem resposta real não há categoria assistida, decisão humana classificativa ou relatório apresentado como concluído.
- Não há OCR, execução de percursos programados, verificação empírica, auditoria jurídica, classificação global, pontuações, ponderações ou limiares.

## Preservação e Git

Git não disponível no PATH nem nos caminhos usuais verificados. Não foi possível criar commit inicial. A implementação prosseguiu conforme autorizado, tendo em conta a cópia de segurança externa declarada. Foi criado um manifesto SHA-256 dos ficheiros preexistentes relevantes; os ficheiros antigos não foram apagados nem reescritos. `.gitignore` foi reforçado para credenciais, ambiente, caches, logs, uploads, temporários e outputs. `.venv` foi preservado.
