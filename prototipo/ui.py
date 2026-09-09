from pathlib import Path
from copy import deepcopy
import json
import pandas as pd
import streamlit as st
from .api import configuration, smoke_test, TechnicalError
from .demo import load_demo, EXAMPLE_ID, EXAMPLE_TITLE, EXAMPLE_DESCRIPTION, EXAMPLE_LIMIT, example_provenance
from .engine import review_criterion, propose
from .extraction import extract, from_text
from .models import Element, Category, SELECTION_RULES
from .norma import ROOT, CRITERIOS, load_norma
from .reporting import export_docx, export_json, sections, readable
from .state import STAGES, new_session, transition, replace_document, save_representation, save_context, answer, decide, now, fingerprint
from .table_export import (CSV_FILENAME, READING_COLUMNS, XLSX_FILENAME,
                           export_reading_csv, export_reading_xlsx, reading_rows)

FIELDS = ("público/destinatários", "função/perfil do respondente", "unidade de resposta", "modo previsto", "finalidade", "objetivos/questões de avaliação", "dimensões principais", "momento da recolha", "estado dos projetos/intervenções")
AVAILABILITY = ["Não sei/Não disponível", "Informado", "Não aplicável", "Incluído no questionário", "Incluído noutro documento"]
VISIBILITY = ["contexto interno fornecido à aplicação", "conteúdo apresentado ao respondente", "conteúdo ainda não incorporado no instrumento", "documento não disponível"]
DOCUMENT_TYPES = ["convite ou apresentação", "instruções", "especificação de filtros e saltos", "objetivos ou questões de avaliação", "matriz de correspondência", "teoria da mudança/modelo lógico", "outro documento metodológico"]
FORMATS = ["não confirmado", "escolha única", "escolha múltipla", "livre", "numérico", "matriz", "ordenação", "instrução", "outro"]
FORMAT_LABELS = {"não confirmado": "Não foi possível confirmar o formato de resposta",
                 "matriz": "Grelha ou tabela de perguntas", "livre": "Resposta livre"}
STAGE_LABELS = {**STAGES, "structure": "Rever a leitura do questionário"}
LIST_FIELDS = ("opcoes", "subitens", "linhas", "colunas", "instrucao_aplica_a")
COLUMN_GUIDANCE = {
    "id": "Identificador único da pergunta, instrução ou bloco. Confirme o código apresentado no questionário original.",
    "texto": "Texto identificado pela aplicação. Confirme se está completo, correto e associado à referência adequada.",
    "localizacao": "Página, secção, bloco ou outra localização que permita encontrar este elemento no documento original.",
    "formato": "Forma prevista para responder: resposta livre, escolha única, escolha múltipla, escala, grelha ou outro formato aplicável.",
    "opcoes": "Introduza cada opção ou ponto da escala numa linha separada, preservando a ordem e os rótulos do questionário original. Por exemplo: ‘Sim’ na primeira linha e ‘Não’ na segunda.",
    "subitens": "Perguntas ou itens distintos apresentados sob uma pergunta ou enunciado comum. Registe um item por linha.",
    "linhas": "Elementos apresentados nas linhas de uma pergunta organizada em grelha ou tabela. Preserve a ordem original.",
    "colunas": "Categorias, opções ou pontos da escala apresentados nas colunas de uma grelha ou tabela. Preserve a ordem original.",
    "instrucoes": "Orientações aplicáveis à pergunta ou ao bloco, incluindo quem deve responder, como responder e eventuais condições de percurso.",
    "instrucao_aplica_a": "Referências das perguntas abrangidas por uma instrução aplicável a várias perguntas. Registe uma referência por linha.",
    "condicoes_destinos": "Condições, filtros ou encaminhamentos e a pergunta ou secção para onde conduzem.",
    "regra_selecao": "Indicação sobre quantas opções podem ou devem ser selecionadas.",
    "numero_minimo": "Número mínimo de respostas ou opções exigidas, quando estiver explicitamente indicado.",
    "numero_maximo": "Número máximo de respostas ou opções permitido, quando estiver explicitamente indicado.",
    "outra_condicao_resposta": "Transcrição exata da condição presente no questionário, apenas quando selecionar «Outra condição indicada no questionário».",
}
COLUMN_HEADER_HELP = {
    "id": "Confirme o identificador no questionário original.",
    "texto": "Confirme o texto completo e a referência associada.",
    "localizacao": "Indique onde encontrar o elemento no original.",
    "formato": "Confirme a forma prevista para responder.",
    "opcoes": "Registe uma opção por linha e preserve a ordem.",
    "subitens": "Registe uma subpergunta por linha.",
    "linhas": "Registe uma linha da grelha por linha.",
    "colunas": "Registe uma coluna da grelha por linha.",
    "instrucoes": "Confirme as orientações aplicáveis ao elemento.",
    "instrucao_aplica_a": "Registe uma referência abrangida por linha.",
    "condicoes_destinos": "Confirme as condições e os respetivos destinos.",
    "regra_selecao": "Escolha a regra explicitamente indicada no original.",
    "numero_minimo": "Introduza um inteiro não negativo, quando aplicável.",
    "numero_maximo": "Introduza um inteiro não negativo, quando aplicável.",
    "outra_condicao_resposta": "Preencha apenas para outra condição indicada no original.",
}


def brand():
    """Um cabeçalho por execução, com imagens locais e disposição nativa adaptável."""
    assets = Path(__file__).resolve().parents[1] / "assets" / "brand"
    # Os grupos passam para a linha seguinte quando falta largura. As imagens
    # conservam a proporção original e nunca excedem a largura do seu grupo.
    with st.container(key="institutional_header"):
        with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
            with st.container(width=190):
                st.caption(
                    'Entidade responsável<br><span style="white-space: nowrap;">IPPS-Iscte</span>',
                    unsafe_allow_html=True,
                )
                st.image(assets / "ipps-iscte.png", width=190)
            with st.container(width=180):
                st.caption("AD&C")
                st.image(assets / "adc.png", width=180)
            with st.container(width=450):
                st.caption("Programa e cofinanciamento")
                st.image(assets / "pat2030-portugal2030-ue.png", width=450)
    st.title("SURV4IMPACT AI")
    st.markdown("**Assistente de Revisão Metodológica de Questionários**")
    # Designações transcritas de criterios_v08.md: enquadramento e secção 1
    # de cada ficha. Os espaços não separáveis ligam o código à designação;
    # o restante texto pode adaptar-se à largura disponível.
    with st.container(border=True, key="methodological_scope", gap="small"):
        st.caption("**Domínio D2\u00a0-\u00a0Conceção, desenho e aplicação do questionário**")
        st.caption("**Critérios analisados:**")
        st.caption(
            "D2.3\u00a0—\u00a0Estrutura e percurso de resposta.  \n"
            "D2.4\u00a0—\u00a0Clareza e adaptação da linguagem.  \n"
            "D2.6\u00a0—\u00a0Opções de resposta e escalas."
        )


def go(s, stage):
    try:
        transition(s, stage)
        st.rerun()
    except ValueError as exc:
        message = str(exc)
        if message == "Confirme a representação necessária antes de iniciar a análise.":
            message = "Confirme que a leitura do questionário está correta antes de iniciar a análise."
        st.warning(message)


def intake(s):
    st.header("Instrumento e contexto")
    st.write(
        "Carregue o questionário em PDF ou DOCX, ou cole o seu conteúdo completo, incluindo perguntas, "
        "instruções, opções de resposta, escalas e indicações de percurso. Antes da análise, poderá verificar "
        "e corrigir a forma como a aplicação interpretou o documento. A análise só começa depois de confirmar "
        "que o conteúdo apresentado corresponde ao questionário original."
    )
    # Posição estável: mudar o aviso não desloca os controlos do formulário.
    current_instrument = st.empty()
    if s["instrumento"]:
        current_instrument.caption("Instrumento atual: " + s["instrumento"].get("designacao", s["instrumento"]["nome"]) + " · " + s["instrumento"].get("versao", "não identificada"))
    st.caption(
        "Escolha o questionário de exemplo ou introduza o seu questionário. Ao usar o exemplo ou confirmar "
        "um novo questionário, o anterior é substituído e o contexto e os resultados associados são limpos. "
        "Descarregue o relatório antes de mudar."
    )
    with st.container(border=True):
        use_example = st.button("Usar questionário de exemplo", key="demo")
        st.caption(EXAMPLE_DESCRIPTION)
        st.caption(EXAMPLE_LIMIT)
        if use_example:
            load_demo(s)
            st.rerun()
    with st.form("instrument_" + s["id"]):
        title = st.text_input("Designação do questionário", value="")
        version = st.text_input("Versão ou data", value="não identificada")
        status = st.selectbox("Estado do questionário", ["em preparação", "revisto", "pronto para aplicação", "outro", "Não sei/Não disponível", "Não aplicável", "Incluído no questionário", "Incluído noutro documento"])
        upload = st.file_uploader("Carregar o seu questionário", type=["pdf", "docx"], max_upload_size=50)
        st.caption("PDF ou DOCX · máximo de 50 MB por ficheiro")
        manual = st.text_area("Representação textual fiel (alternativa ao ficheiro)", height=150)
        scope = st.selectbox("Âmbito do conteúdo fornecido", ["integral", "recorte localizado"])
        st.caption("Substituir o instrumento inicia uma sessão nova, sem resultados ou decisões do anterior. Descarregue o relatório antes de substituir.")
        submitted = st.form_submit_button("Extrair / substituir instrumento", type="primary")
    if submitted:
        try:
            instrument, representation = extract(upload.getvalue(), upload.name) if upload else from_text(manual)
            instrument.update(designacao=title or instrument.get("titulo_extraido") or instrument["nome"], versao=version or "não identificada", estado=status)
            replace_document(s, instrument, representation)
            s["ambito"] = scope
            st.rerun()
        except Exception:
            st.error("Não foi possível extrair este documento. Confirme o formato, o limite de 50 MB e se contém texto selecionável. Pode introduzir uma representação textual fiel; uma falha de leitura não é uma falha metodológica.")
    if not s["instrumento"]:
        return
    st.subheader("Contexto necessário")
    st.caption("Não invente informação. Identifique a disponibilidade e quem recebe cada conteúdo. Modo previsto: online, papel, CATI, presencial, misto ou ainda não definido.")
    rows = [{"campo": field, **s["contexto"].get(field, {"valor": "", "disponibilidade": AVAILABILITY[0], "visibilidade": VISIBILITY[0]})} for field in FIELDS]
    with st.form("context_" + s["id"]):
        edited = st.data_editor(pd.DataFrame(rows), hide_index=True, disabled=["campo"], column_config={
            "disponibilidade": st.column_config.SelectboxColumn(options=AVAILABILITY, required=True),
            "visibilidade": st.column_config.SelectboxColumn(options=VISIBILITY, required=True)}, key="context_editor_" + s["id"])
        if st.form_submit_button("Guardar contexto"):
            save_context(s, {r.pop("campo"): r for r in edited.to_dict("records")}, s["documentos"])
            st.success("Contexto guardado com proveniência.")
    st.subheader("Documentos complementares, quando existam")
    st.caption("Uma matriz de correspondência ou teoria da mudança não é obrigatória por princípio.")
    with st.form("complement_" + s["id"], clear_on_submit=True):
        kind = st.selectbox("Tipo de documento", DOCUMENT_TYPES)
        docname = st.text_input("Nome, versão ou referência documental")
        visibility = st.selectbox("Proveniência e visibilidade", VISIBILITY)
        file = st.file_uploader("Documento complementar PDF/DOCX", type=["pdf", "docx"])
        text = st.text_area("Texto pertinente / localização / indicação de indisponibilidade")
        confirmed = st.checkbox("Confirmei a fidelidade do texto complementar, quando fornecido")
        if st.form_submit_button("Adicionar documento / referência"):
            try:
                doc = {"tipo": kind, "nome": docname, "visibilidade": visibility, "texto": text, "confirmado": confirmed}
                if file:
                    extracted, _ = extract(file.getvalue(), file.name)
                    doc.update(nome=docname or file.name, sha256=extracted["sha256"], texto="\n".join(r["localizacao"] + "\n" + r["texto"] for r in extracted["texto_bruto"]), confirmado=False)
                if not doc["nome"] and not doc["texto"]:
                    raise ValueError("Identifique o documento ou a indisponibilidade.")
                save_context(s, s["contexto"], s["documentos"] + [doc])
                st.rerun()
            except Exception:
                st.error("Documento não adicionado. Identifique-o e, se a extração falhar, forneça o texto pertinente.")
    for i, d in enumerate(s["documentos"]):
        with st.expander(d["tipo"] + " — " + d["nome"]):
            with st.form(f"doc_{s['id']}_{i}"):
                content = st.text_area("Conferir/corrigir texto e localizadores", d["texto"], height=200)
                faithful = st.checkbox("Texto conferido com o original", value=d["confirmado"])
                if st.form_submit_button("Guardar confirmação documental"):
                    docs = deepcopy(s["documentos"])
                    docs[i].update(texto=content, confirmado=faithful)
                    save_context(s, s["contexto"], docs)
                    st.rerun()
    if st.button("Continuar para rever a leitura do questionário", type="primary"):
        go(s, "structure")


def structure(s):
    st.header(STAGE_LABELS["structure"])
    st.info(
        "A aplicação identificou automaticamente as perguntas e os restantes elementos do questionário. "
        "Compare o conteúdo apresentado abaixo com o documento original e corrija eventuais diferenças antes de prosseguir.\n\n"
        "Verifique especialmente o texto e a ordem das perguntas, as instruções, as opções e escalas de resposta, "
        "as perguntas organizadas em grelhas ou tabelas e as condições de percurso. Se não for possível identificar "
        "o formato de resposta, assinale que essa informação não está confirmada."
    )
    with st.expander("Texto lido do documento e localização no original", expanded=False):
        for block in s["instrumento"]["texto_bruto"]:
            st.caption(block["localizacao"])
            st.text(block["texto"])
        for warning in s["instrumento"].get("avisos", []):
            st.warning({
                "Alguns caracteres do PDF podem ter sido mapeados incorretamente pela fonte incorporada.":
                    "Alguns caracteres do PDF podem ter sido lidos incorretamente. Compare-os com o original.",
            }.get(warning, warning))
        if s["instrumento"].get("instrucoes_candidatas"):
            st.write("Instruções identificadas pela aplicação: indique na tabela a que perguntas se aplicam.")
            for instruction in s["instrumento"]["instrucoes_candidatas"]:
                st.write(instruction)
    st.caption("Cada linha corresponde a uma pergunta, instrução ou conjunto de perguntas. Nas células com listas, escreva cada opção ou subpergunta numa linha separada.")
    st.caption("Uma diferença na leitura automática não significa que exista um problema no questionário. Corrigir esta leitura não altera o documento original. Se já houver uma análise, será necessário voltar a analisar os resultados afetados pelas correções.")
    rows = reading_rows(s["representacao"])
    editor_rows = pd.DataFrame(rows)
    for key in ("numero_minimo", "numero_maximo"):
        editor_rows[key] = pd.to_numeric(editor_rows[key], errors="coerce")
    st.download_button(
        "Descarregar tabela em Excel",
        export_reading_xlsx(s["representacao"]),
        XLSX_FILENAME,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
    with st.expander("Outros formatos", expanded=False):
        st.download_button(
            "Descarregar em CSV",
            export_reading_csv(s["representacao"]),
            CSV_FILENAME,
            "text/csv",
        )
    # A versão instalada não permite traduzir ou desativar apenas este comando
    # da barra do editor. Ocultamo-lo porque os downloads próprios estão acima.
    st.html('<style>button[aria-label="Download as CSV"]{display:none!important}</style>')
    st.write("Compare cada linha com o questionário original. Corrija os elementos que não tenham sido identificados corretamente e assinale como não confirmada a informação que não consiga verificar.")
    with st.expander("Como rever esta tabela", expanded=False):
        for key, label in READING_COLUMNS:
            st.markdown(f"**{label}:** {COLUMN_GUIDANCE[key]}")
    option_elements = [element for element in s["representacao"] if element.get("opcoes")]
    if option_elements:
        with st.expander("Ver ou editar opções e escalas por pergunta", expanded=False):
            st.caption("As opções são apresentadas e guardadas uma por linha. A ordem e o texto são preservados na tabela, no Excel e no CSV.")
            option_ids = [element["id"] for element in option_elements]
            selected_id = st.selectbox(
                "Pergunta a rever",
                option_ids,
                key=f"option_detail_select_{s['id']}_{s['revisao']}",
            )
            selected = next(element for element in option_elements if element["id"] == selected_id)
            option_text = st.text_area(
                "Opções ou escala de resposta — uma por linha",
                value="\n".join(selected["opcoes"]),
                height=180,
                key=f"option_detail_text_{s['id']}_{s['revisao']}_{selected_id}",
            )
            if st.button("Guardar opções desta pergunta", key=f"option_detail_save_{s['id']}_{s['revisao']}_{selected_id}"):
                options = [value.strip() for value in option_text.splitlines() if value.strip()]
                elements = deepcopy(s["representacao"])
                index = next(i for i, element in enumerate(elements) if element["id"] == selected_id)
                elements[index]["opcoes"] = options
                save_representation(s, elements, False, reason="correção das opções na leitura do questionário")
                st.rerun()
    confirmation_key = f"confirm_reading_{s['id']}_{s['revisao']}"
    with st.form(f"structure_{s['id']}_{s['revisao']}", enter_to_submit=False):
        editor = st.data_editor(editor_rows, num_rows="dynamic", hide_index=True, width="stretch", column_config={
            "id": st.column_config.TextColumn(dict(READING_COLUMNS)["id"], help=COLUMN_HEADER_HELP["id"]),
            "texto": st.column_config.TextColumn(dict(READING_COLUMNS)["texto"], width="large", help=COLUMN_HEADER_HELP["texto"]),
            "localizacao": st.column_config.TextColumn(dict(READING_COLUMNS)["localizacao"], help=COLUMN_HEADER_HELP["localizacao"]),
            "formato": st.column_config.SelectboxColumn(dict(READING_COLUMNS)["formato"], options=FORMATS, format_func=lambda value: FORMAT_LABELS.get(value, value), help=COLUMN_HEADER_HELP["formato"]),
            "opcoes": st.column_config.TextColumn(dict(READING_COLUMNS)["opcoes"], help=COLUMN_HEADER_HELP["opcoes"]),
            "subitens": st.column_config.TextColumn(dict(READING_COLUMNS)["subitens"], help=COLUMN_HEADER_HELP["subitens"]),
            "linhas": st.column_config.TextColumn(dict(READING_COLUMNS)["linhas"], help=COLUMN_HEADER_HELP["linhas"]),
            "colunas": st.column_config.TextColumn(dict(READING_COLUMNS)["colunas"], help=COLUMN_HEADER_HELP["colunas"]),
            "instrucoes": st.column_config.TextColumn(dict(READING_COLUMNS)["instrucoes"], help=COLUMN_HEADER_HELP["instrucoes"]),
            "instrucao_aplica_a": st.column_config.TextColumn(dict(READING_COLUMNS)["instrucao_aplica_a"], help=COLUMN_HEADER_HELP["instrucao_aplica_a"]),
            "condicoes_destinos": st.column_config.TextColumn(dict(READING_COLUMNS)["condicoes_destinos"], help=COLUMN_HEADER_HELP["condicoes_destinos"]),
            "regra_selecao": st.column_config.SelectboxColumn(dict(READING_COLUMNS)["regra_selecao"], options=SELECTION_RULES, required=True, help=COLUMN_HEADER_HELP["regra_selecao"]),
            "numero_minimo": st.column_config.NumberColumn(dict(READING_COLUMNS)["numero_minimo"], min_value=0, step=1, format="%d", help=COLUMN_HEADER_HELP["numero_minimo"]),
            "numero_maximo": st.column_config.NumberColumn(dict(READING_COLUMNS)["numero_maximo"], min_value=0, step=1, format="%d", help=COLUMN_HEADER_HELP["numero_maximo"]),
            "outra_condicao_resposta": st.column_config.TextColumn(dict(READING_COLUMNS)["outra_condicao_resposta"], width="large", help=COLUMN_HEADER_HELP["outra_condicao_resposta"]),
        }, key=f"repr_{s['id']}_{s['revisao']}")
        with st.expander("Substituir toda a leitura automática (opcional)", expanded=False):
            st.write(
                "Utilize esta opção apenas se a leitura automática estiver demasiado incompleta para ser corrigida diretamente na tabela. "
                "Cole o conteúdo completo do questionário, incluindo perguntas, instruções, opções e escalas de resposta e condições de percurso.\n\n"
                "O conteúdo introduzido substituirá integralmente a leitura apresentada na tabela."
            )
            textual = st.text_area("Conteúdo completo do questionário", height=140)
            st.caption("Se tiver colado apenas uma parte do questionário, indique as páginas, a secção ou o bloco correspondente. Esta informação será utilizada apenas para identificar a origem do conteúdo no relatório.")
            local = st.selectbox(
                "Localização no documento original (opcional)",
                ["Questionário completo"],
                index=None,
                placeholder="Ex.: páginas 4–8, Bloco B — Satisfação",
                accept_new_options=True,
            )
            st.warning("Esta operação substituirá os elementos apresentados na tabela. Depois da substituição, terá de rever e confirmar novamente a leitura do questionário.")
            replace_reading = st.form_submit_button("Substituir a leitura automática")
            if replace_reading:
                if not textual.strip():
                    st.error("Cole o conteúdo completo do questionário antes de substituir a leitura.")
                else:
                    source_location = local.strip() if isinstance(local, str) and local.strip() else "Localização não indicada pelo utilizador"
                    # Esta localização serve apenas a rastreabilidade e fica fora
                    # do payload metodológico. O elemento conserva um localizador
                    # técnico neutro exigido pelo modelo interno de dados.
                    s["rastreabilidade_substituicao"] = {
                        "localizacao_documento_original": source_location,
                        "finalidade": "identificação da origem do conteúdo no relatório",
                    }
                    elements = [Element(id="TEXTO", texto=textual, localizacao="Conteúdo introduzido pelo utilizador").model_dump()]
                    save_representation(s, elements, False)
                    # A confirmação é sempre renovada, mesmo quando o texto
                    # substituto coincide com o anterior e a revisão não muda.
                    st.session_state[confirmation_key] = False
                    st.rerun()
        explicit = st.checkbox("Confirmo que a leitura está correta e corresponde ao questionário original, mantendo assinaladas as situações em que não foi possível confirmar o formato de resposta", key=confirmation_key)
        saved = st.form_submit_button("Guardar leitura e confirmação", type="primary")
    if saved:
        try:
            elements = []
            for row in editor.fillna("").to_dict("records"):
                for k in LIST_FIELDS:
                    row[k] = [v.strip() for v in row[k].splitlines() if v.strip()]
                row["formato"] = row["formato"] or "não confirmado"
                for key in ("numero_minimo", "numero_maximo"):
                    row[key] = None if row[key] == "" else int(row[key])
                elements.append(row)
            save_representation(s, elements, explicit)
            st.rerun()
        except ValueError as exc:
            st.error({
                "Cada elemento precisa de identificador, texto e localização.": "Preencha a referência, o texto e a localização no original de cada pergunta, instrução ou bloco.",
                "Os identificadores devem ser únicos.": "Use uma referência diferente para cada pergunta, instrução ou bloco.",
            }.get(str(exc), "Não foi possível guardar a leitura. Verifique os campos da tabela: cada elemento deve ter uma referência, texto e localização no original; nas listas, use uma entrada por linha."))
    st.write("Estado: " + ("Leitura do questionário confirmada" if s["confirmada"] else "A aguardar a sua confirmação da leitura do questionário"))
    if st.button("Continuar para apreciação", disabled=not s["confirmada"]):
        go(s, "review")


def review(s, key, model):
    st.header("Apreciação documental")
    st.write("São analisados apenas D2.3, D2.4 e D2.6. Os resultados e as classificações são propostas sujeitas a decisão humana.")
    if not key:
        st.warning("API sem configuração: análise assistida não executada. Pode continuar para o relatório parcial.")
    unconfirmed_docs = any(d["texto"] and not d["confirmado"] for d in s["documentos"])
    if unconfirmed_docs:
        st.warning("Confirme primeiro o texto dos documentos complementares em Instrumento e contexto.")
    consent = st.checkbox("Enviar à API o instrumento, contexto e documentos confirmados para esta análise", key="send_" + s["id"])
    st.caption("A API recebe apenas as secções normativas pertinentes. Os documentos de testes não integram o prompt normal.")
    if st.button("Executar verificações pendentes", disabled=not key or not consent or unconfirmed_docs or not s["confirmada"], type="primary"):
        with st.status("A apreciar os critérios…", expanded=True) as status:
            failed = False
            for c in CRITERIOS:
                try:
                    st.write(c + ": verificações ainda sem resultado atual")
                    review_criterion(s, c, key, model)
                except (TechnicalError, ValueError) as exc:
                    s["api"] = {"sucesso": False, "modelo": model, "erro_tecnico": str(exc)}
                    st.error(c + ": " + str(exc))
                    failed = True
            status.update(label="Execução com limitações técnicas" if failed else "Verificações recebidas — propostas por validar", state="error" if failed else "complete")
    for c in CRITERIOS:
        with st.expander(c + " — evidência e observações", expanded=True):
            values = [v for r, v in s["verificacoes"].items() if r.startswith(c)]
            if not values:
                st.write("Por concluir; sem análise real disponível.")
            for v in values:
                st.write(v["regra"] + " · " + v["estado"])
                st.write(v["fundamento"])
                for o in v["observacoes"]:
                    st.write(readable(o))
                if v["pendencia_metodologica"]:
                    st.warning("Decisão metodológica pendente: " + v["pendencia_metodologica"])
    if st.button("Continuar para esclarecimentos"):
        go(s, "clarifications")


def clarifications(s):
    st.header("Esclarecimentos e ações")
    if not s["pedidos"]:
        st.info("Não há pedidos dirigidos registados. Isto não demonstra adequação do instrumento.")
    for p in s["pedidos"]:
        with st.expander(p["regra"] + " — " + p["pergunta"], expanded=p["estado"] == "pendente"):
            st.write(p["justificacao"])
            st.write("Estado: " + p["estado"])
            for response in p["respostas"]:
                st.write(readable(response))
            with st.form("answer_" + s["id"] + p["id"]):
                response = st.text_area("Resposta ou declaração de indisponibilidade")
                visibility = st.selectbox("A resposta corresponde a", VISIBILITY)
                unavailable = st.checkbox("Não disponho desta informação")
                close = st.checkbox("Opto expressamente por fechar sem fornecer a informação")
                if st.form_submit_button("Guardar resposta / fecho"):
                    try:
                        answer(s, p["id"], response, visibility, unavailable, close)
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
    st.caption("Após guardar, retome a apreciação: repetem-se apenas as verificações dependentes. Fecho por falta documental e limitação técnica têm tratamentos distintos. O silêncio não fecha pedidos.")
    for aid, action in s["acoes"].items():
        with st.expander("Ação — " + action["regra"] + " · " + action["elemento"]):
            if action.get("estado") == "retirada para reapreciação":
                st.info("Ação retirada enquanto se reaprecia a evidência dependente. Conservada no histórico; não deve ser aplicada como proposta atual.")
                continue
            st.write("Alteração necessária: " + action["alteracao_necessaria"])
            st.write("Proposta de redação: " + action["proposta_redacao"])
            st.write("Incorporação confirmada: " + ("sim" if action["incorporada"] else "não"))
            with st.form("action_" + s["id"] + aid):
                accepted = st.checkbox("Aceito a proposta para realização", value=action["aceite"])
                if st.form_submit_button("Guardar aceitação"):
                    action["aceite"] = accepted
                    st.success("Decisão guardada. A aceitação não altera a versão analisada.")
            with st.form("incorporated_" + s["id"] + aid):
                eid = st.selectbox("Elemento efetivamente revisto", [e["id"] for e in s["representacao"]])
                revised = st.text_area("Texto efetivamente incorporado (inclua opções/instruções alteradas)")
                version = st.text_input("Identificação da versão revista")
                location = st.text_input("Localização na versão revista")
                explicit = st.checkbox("Conferi e confirmo a incorporação no instrumento revisto")
                if st.form_submit_button("Registar incorporação e reapreciar representação"):
                    if not explicit or not all(x.strip() for x in (revised, version, location)):
                        st.error("É necessária confirmação expressa, texto, versão e localização.")
                    else:
                        elements = deepcopy(s["representacao"])
                        idx = next(i for i, e in enumerate(elements) if e["id"] == eid)
                        elements[idx] = Element(id=eid, texto=revised, localizacao=location).model_dump()
                        s["historico"].append({"data": now(), "tipo": "identificação da versão revista", "versao_anterior": s["instrumento"].get("versao"), "versao_revista": version, "localizacao": location})
                        save_representation(s, elements, False, "alteração confirmada do instrumento")
                        action.update(incorporada=True, versao_revista=version, localizacao=location, estado="incorporada — a reapreciar")
                        s["instrumento"].setdefault("sha256_fonte_original", s["instrumento"]["sha256"])
                        s["instrumento"]["sha256"] = fingerprint(elements)
                        s["instrumento"]["tipo_hash"] = "representação textual da versão revista confirmada; ficheiro revisto não carregado"
                        s["instrumento"].setdefault("evidencias_revisao", []).append({"texto": revised, "localizacao": location, "versao": version, "data": now()})
                        s["instrumento"]["versao"] = version
                        go(s, "structure")
    with st.container(horizontal=True):
        if st.button("Retomar verificações dependentes"):
            go(s, "review")
        if st.button("Continuar para decisão humana"):
            go(s, "decisions")


def decisions(s, key, model):
    st.header("Decisão humana")
    st.caption("Uma categoria por critério, apenas quando a apreciação estiver concluída. Os estados de espera não são categorias.")
    for c in CRITERIOS:
        with st.container(border=True):
            st.subheader(c)
            if st.button("Preparar proposta fundamentada — " + c, disabled=not key, key="propose_" + c):
                try:
                    with st.spinner("A fundamentar a proposta…"):
                        propose(s, c, key, model)
                    st.rerun()
                except (ValueError, TechnicalError) as exc:
                    s["api"] = {"sucesso": False, "modelo": model, "erro_tecnico": str(exc)}
                    st.error(str(exc))
            p = s["propostas"].get(c)
            if not p:
                st.write("Por concluir — sem categoria proposta.")
                continue
            st.write(readable(p))
            if not p["categoria"]:
                continue
            with st.form("decision_" + s["id"] + c):
                category = st.selectbox("Categoria decidida", list(Category.__args__), index=list(Category.__args__).index(p["categoria"]))
                reviewer = st.text_input("Responsável pela decisão")
                rationale = st.text_area("Fundamentação da decisão humana")
                explicit = st.checkbox("Valido expressamente esta decisão para a versão analisada")
                if st.form_submit_button("Guardar decisão — " + c):
                    try:
                        decide(s, c, category, rationale, reviewer, explicit)
                        st.success("Decisão humana registada.")
                    except ValueError as exc:
                        st.error(str(exc))
            if c in s["decisoes"]:
                st.write(readable(s["decisoes"][c]))
    if st.button("Preparar relatório", type="primary"):
        go(s, "report")


def report(s):
    st.header("Relatório")
    for heading, paragraphs in sections(s):
        with st.expander(heading, expanded=heading == "Identificação"):
            for text in paragraphs:
                st.write(text)
    with st.container(horizontal=True):
        st.download_button("Descarregar DOCX", export_docx(s), "surv4impact_relatorio_prototipo.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        st.download_button("Descarregar JSON", export_json(s), "surv4impact_relatorio_prototipo.json", "application/json")


def main():
    st.set_page_config(page_title="SURV4IMPACT AI — Protótipo", layout="wide", initial_sidebar_state="expanded")
    st.session_state.setdefault("prototype", new_session())
    s = st.session_state.prototype
    brand()
    example_notice = st.empty()
    if s["instrumento"].get("exemplo_id") == EXAMPLE_ID:
        with example_notice.container():
            st.caption(EXAMPLE_TITLE)
            st.caption(EXAMPLE_LIMIT)
            with st.expander("Sobre o questionário de exemplo", expanded=False):
                reference = example_provenance()
                st.write("Este questionário foi construído para fins de demonstração, utilizando elementos de casos de teste metodologicamente aprovados. Não corresponde a um questionário histórico original.")
                st.write("Os comportamentos esperados nos casos de origem foram validados. A combinação dos elementos, as adaptações ao público-alvo e ao contexto e a classificação integral deste questionário ilustrativo não foram objeto de validação metodológica autónoma.")
                rule_names = {code: body.splitlines()[0].split(" — ", 1)[1]
                              for code, body in load_norma()["regras"].items()}
                # Markdown nativo: parágrafos separados e código ligado ao início
                # do título; o restante título pode quebrar conforme a largura.
                st.table([{
                    "Caso de teste aprovado": g["caso"],
                    "Elementos do caso de teste utilizados": ", ".join(g["elementos"]),
                    "Regras abrangidas no caso de origem": "\n\n".join(
                        code.replace("-", "\u2060-\u2060") + "\u00a0—\u00a0" + rule_names[code]
                        for code in g["regras"]),
                } for g in reference["grupos"]], width="stretch", hide_index=True, hide_header=False)
                st.caption("Os resultados esperados dos casos de origem servem apenas como referência para a validação do protótipo e não determinam os resultados desta análise. Em P7, as quatro alternativas estão confirmadas, mas continua por confirmar se deve ser selecionada uma ou várias. Não existe uma classificação integral predefinida para este questionário de exemplo.")
    key, default_model = configuration()
    with st.sidebar:
        st.subheader("Percurso")
        for stage, label in STAGE_LABELS.items():
            if st.button(label, key="nav_" + stage, type="primary" if s["stage"] == stage else "secondary"):
                go(s, stage)
        if st.button("Nova análise", key="reset"):
            st.session_state.prototype = new_session()
            for name in list(st.session_state):
                if name != "prototype":
                    del st.session_state[name]
            st.rerun()
        st.divider()
        with st.expander("Configuração técnica"):
            session_key = st.text_input("Chave API para esta sessão (opcional)", type="password", key="session_api_key")
            key = session_key or key
            model = st.text_input("Modelo", value=default_model, key="api_model")
            if st.button("Testar API com conteúdo sintético"):
                s["api"] = smoke_test(key, model)
            if s["api"]:
                st.write(s["api"])
            st.caption("Alternativa: OPENAI_API_KEY e OPENAI_MODEL no ambiente ou .streamlit/secrets.toml. Credenciais não integram o relatório.")
        st.caption("API configurada" if key else "API não configurada")
        st.caption("V08 · " + s["norma"]["sha256"][:12])
    if not key and not s["api"]:
        s["api"] = smoke_test("", model)
    if s["stage"] not in STAGES:
        st.error("Estado de navegação inválido. Inicie uma nova análise.")
        return
    if s["stage"] == "intake":
        intake(s)
    elif s["stage"] == "structure":
        structure(s)
    elif s["stage"] == "review":
        review(s, key, model)
    elif s["stage"] == "clarifications":
        clarifications(s)
    elif s["stage"] == "decisions":
        decisions(s, key, model)
    elif s["stage"] == "report":
        report(s)
