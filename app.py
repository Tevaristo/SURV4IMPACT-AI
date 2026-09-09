from __future__ import annotations

import base64
import html
import os
from collections import Counter
from functools import lru_cache
from pathlib import Path

import pandas as pd
import streamlit as st

from surv4impact import __version__
from surv4impact.ai import improve_question, run_ai_review
from surv4impact.demo import demo_questionnaire
from surv4impact.knowledge import criterion_label, p0_catalog
from surv4impact.models import Finding, QuestionnaireMetadata
from surv4impact.parser import (
    QuestionnaireParseError,
    parse_questionnaire,
    reclassify_questions,
)
from surv4impact.reporting import export_docx, export_json, export_xlsx, findings_dataframe
from surv4impact.rules import SEVERITY_ORDER, run_deterministic_review
from surv4impact.synthesis import synthesise


PROJECT_ROOT = Path(__file__).resolve().parent
BRAND_ASSETS = PROJECT_ROOT / "assets" / "brand"
STAGES = ["Carregar", "Leitura do Questionário", "Análise", "Síntese", "Exportar Relatório"]
SEVERITIES = ["Crítica", "Elevada", "Moderada", "Baixa", "Informativa"]
DECISIONS = ["Pendente", "Aceitar", "Modificar", "Rejeitar", "N.A."]
DEFAULT_ANALYSIS_TITLE = QuestionnaireMetadata().title


st.set_page_config(
    page_title="SURV4IMPACT AI — Revisor de Questionários",
    page_icon=":material/fact_check:",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(f"<style>{(PROJECT_ROOT / 'assets' / 'styles.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def init_state() -> None:
    defaults = {
        "stage": "Carregar",
        "questionnaire": None,
        "uploaded_file_bytes": None,
        "uploaded_file_name": "",
        "custom_analysis_title": "",
        "replace_file": False,
        "upload_generation": 0,
        "metadata": QuestionnaireMetadata(),
        "findings": [],
        "analysis_source": "",
        "ai_used": False,
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": os.getenv("OPENAI_MODEL", "gpt-5.6"),
        "enable_ai": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


@lru_cache(maxsize=8)
def image_data_uri(path: str) -> str:
    encoded = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def brand_system() -> None:
    """Show promoter, institutional partner and cofinancing marks on every view."""
    ipps_logo = image_data_uri(str(BRAND_ASSETS / "ipps-iscte.png"))
    adc_logo = image_data_uri(str(BRAND_ASSETS / "adc.png"))
    funding_logos = image_data_uri(str(BRAND_ASSETS / "pat2030-portugal2030-ue.png"))
    st.markdown(
        f"""
        <section class="surv-brand-system" aria-label="Identidade institucional e cofinanciamento">
          <div class="surv-brand-group surv-brand-institutions">
            <div class="surv-brand-label">Entidade Responsável</div>
            <div class="surv-partner-logos">
              <img class="surv-logo-ipps" src="{ipps_logo}"
                   alt="IPPS-Iscte — Melhores Políticas Públicas">
              <span class="surv-brand-divider" aria-hidden="true"></span>
              <img class="surv-logo-adc" src="{adc_logo}"
                   alt="AD&amp;C — Agência para o Desenvolvimento e Coesão, I.P.">
            </div>
          </div>
          <div class="surv-brand-group surv-brand-funding">
            <div class="surv-brand-label">Programa e cofinanciamento</div>
            <img class="surv-logo-funding" src="{funding_logos}"
                 alt="PAT 2030, Portugal 2030 e Cofinanciado pela União Europeia">
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def hero() -> None:
    st.markdown(
        """
        <div class="surv-hero">
          <div class="surv-product-mark">SURV4IMPACT <span>AI</span></div>
          <div class="surv-eyebrow">Ferramenta de revisão · Domínio 2 - Conceção, Desenho e Aplicação</div>
          <h1>Assistente de Revisão Metodológica de Questionários</h1>
          <p>Revisão baseada na matriz de análise simplificada.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stepper() -> None:
    current = STAGES.index(st.session_state.stage)
    parts = []
    for index, stage in enumerate(STAGES):
        state = "active" if index == current else "done" if index < current else ""
        parts.append(f'<div class="surv-step {state}">{index + 1}. {esc(stage)}</div>')
    st.markdown('<div class="surv-stepper">' + "".join(parts) + "</div>", unsafe_allow_html=True)


def kpi(label: str, value: object, note: str = "") -> None:
    st.markdown(
        f'<div class="surv-kpi"><div class="label">{esc(label)}</div>'
        f'<div class="value">{esc(value)}</div><div class="note">{esc(note)}</div></div>',
        unsafe_allow_html=True,
    )


def badge(text: str, css_class: str = "") -> str:
    return f'<span class="surv-badge {css_class}">{esc(text)}</span>'


def severity_class(severity: str) -> str:
    return {
        "Crítica": "critical",
        "Elevada": "high",
        "Moderada": "medium",
        "Baixa": "low",
        "Informativa": "info",
    }.get(severity, "")


def navigate(stage: str) -> None:
    st.session_state.stage = stage
    st.rerun()


def back_button(label: str, destination: str, key: str) -> None:
    if st.button(f"← {label}", key=key):
        navigate(destination)


def seed_context_widgets() -> None:
    """Restore context fields when the user returns to the upload step."""
    metadata = st.session_state.metadata
    values = {
        "home_title": st.session_state.custom_analysis_title,
        "home_mode": metadata.application_mode,
        "home_device": metadata.primary_device,
        "home_audience": metadata.target_audience,
        "home_profile": metadata.audience_profile,
        "home_access": metadata.accessibility_needs,
        "home_accommodations": metadata.accommodations,
        "home_progress": metadata.has_progress_indicator,
        "home_routing": metadata.automatic_routing,
        "home_tested": metadata.tested_on_device,
        "home_layout": metadata.layout_evidence_available,
        "home_notes": metadata.notes,
    }
    for key, value in values.items():
        if key not in st.session_state:
            st.session_state[key] = value


def analyse(questionnaire, metadata: QuestionnaireMetadata, *, use_ai: bool) -> None:
    with st.status("A analisar o questionário…", expanded=True) as status:
        st.write("✓ Estrutura do questionário identificada")
        deterministic = run_deterministic_review(questionnaire, metadata)
        st.write(f"✓ {len(deterministic)} alertas estruturais e linguísticos gerados")
        findings = deterministic
        ai_used = False
        if use_ai:
            if not st.session_state.api_key:
                status.update(label="Revisão local concluída; chave de API em falta", state="error")
                st.warning("A revisão semântica não foi executada porque a chave da API não foi indicada.")
            else:
                st.write("○ Revisão semântica segundo os critérios P0…")
                try:
                    semantic = run_ai_review(
                        questionnaire,
                        metadata,
                        api_key=st.session_state.api_key,
                        model=st.session_state.model,
                    )
                    findings.extend(semantic)
                    ai_used = True
                    st.write(f"✓ {len(semantic)} propostas semânticas geradas")
                except Exception as exc:  # shown to the local evaluator, without hiding the local result
                    st.error(f"A revisão de IA não foi concluída: {exc}")
        st.write("✓ Constatações preparadas para validação pericial")
        status.update(label="Análise concluída", state="complete", expanded=False)
    st.session_state.questionnaire = questionnaire
    st.session_state.metadata = metadata
    st.session_state.findings = findings
    st.session_state.ai_used = ai_used


def metadata_from_form(prefix: str = "home") -> QuestionnaireMetadata:
    return QuestionnaireMetadata(
        title=st.session_state.get(f"{prefix}_title", ""),
        application_mode=st.session_state.get(f"{prefix}_mode", ""),
        primary_device=st.session_state.get(f"{prefix}_device", ""),
        target_audience=st.session_state.get(f"{prefix}_audience", ""),
        audience_profile=st.session_state.get(f"{prefix}_profile", ""),
        accessibility_needs=st.session_state.get(f"{prefix}_access", ""),
        accommodations=st.session_state.get(f"{prefix}_accommodations", ""),
        has_progress_indicator=st.session_state.get(f"{prefix}_progress"),
        automatic_routing=st.session_state.get(f"{prefix}_routing"),
        tested_on_device=st.session_state.get(f"{prefix}_tested"),
        layout_evidence_available=st.session_state.get(f"{prefix}_layout", False),
        notes=st.session_state.get(f"{prefix}_notes", ""),
    )


def tri_state(label: str, key: str, help_text: str = "") -> None:
    st.selectbox(
        label,
        options=[None, True, False],
        format_func=lambda value: {None: "Não confirmado", True: "Sim", False: "Não"}[value],
        key=key,
        help=help_text,
    )


def page_upload() -> None:
    seed_context_widgets()
    st.subheader("Carregar e contextualizar o questionário")
    st.caption("O contexto de aplicação do questionário é fundamental para a análise da adequação metodológica do instrumento. Dê o máximo de detalhe possível.")

    current_questionnaire = st.session_state.questionnaire
    if current_questionnaire is not None:
        st.info(
            f"Análise atual: **{current_questionnaire.title}**. Pode alterar o contexto e "
            "reanalisar sem carregar novamente o ficheiro."
        )

    left, right = st.columns([1.08, 0.92], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("#### 1. Questionário")
            retained_name = (
                st.session_state.uploaded_file_name
                or st.session_state.analysis_source
                or (current_questionnaire.source_name if current_questionnaire else "")
            )
            if current_questionnaire is not None and not st.session_state.replace_file:
                st.success(f"✓ Ficheiro mantido na sessão: {retained_name}")
                st.caption(
                    "Pode voltar às etapas anteriores e reanalisar sem selecionar novamente o ficheiro."
                )
                if st.button("Substituir ficheiro", key="replace-file", width="stretch"):
                    st.session_state.replace_file = True
                    st.session_state.upload_generation += 1
                    st.rerun()
                uploaded = None
            else:
                uploaded = st.file_uploader(
                    "Ficheiro DOCX ou PDF",
                    type=["docx", "pdf"],
                    key=f"questionnaire_upload_{st.session_state.upload_generation}",
                    help=(
                        "Carregue um DOCX com texto editável ou um PDF digital com texto "
                        "selecionável. PDFs digitalizados ou compostos apenas por imagens "
                        "não são processados, porque esta versão não inclui OCR."
                    ),
                )
                if current_questionnaire is not None and st.button(
                    "Cancelar substituição", key="cancel-replace-file", width="stretch"
                ):
                    st.session_state.replace_file = False
                    st.rerun()
            st.text_input("Título do questionário", key="home_title", placeholder="Ex.: Questionário a beneficiários do Pessoas 2030")
            st.markdown(
                '<div class="surv-note">Privacidade: o ficheiro é tratado na sessão. '
                "Só o texto estruturado é enviado ao serviço de IA quando essa opção é ativada.</div>",
                unsafe_allow_html=True,
            )
            st.write("")
            use_demo = st.button("Usar exemplo demonstrativo", width="stretch")

    with right:
        with st.container(border=True):
            st.markdown("#### 2. Contexto de aplicação")
            st.selectbox(
                "Modo de aplicação",
                ["", "Online autoaplicado", "Papel autoaplicado", "Telefónico/CATI", "Entrevista presencial assistida", "Misto"],
                key="home_mode",
            )
            st.selectbox(
                "Dispositivo principal",
                ["", "Computador", "Telemóvel", "Tablet", "Papel", "Oralidade sem apoio visual", "Misto"],
                key="home_device",
            )
            st.text_input("Público-alvo", key="home_audience", placeholder="Quem responde?")
            st.text_area(
                "Perfil do público",
                key="home_profile",
                placeholder="Literacia, familiaridade temática, heterogeneidade, acesso…",
                height=88,
            )
            with st.expander("Acessibilidade e evidência técnica"):
                st.text_area("Necessidades relevantes", key="home_access", height=70)
                st.text_area("Adaptações previstas", key="home_accommodations", height=70)
                tri_state("Indicador de progresso", "home_progress")
                tri_state("Routing automático", "home_routing")
                tri_state("Testado no dispositivo real", "home_tested")
                st.checkbox("Capturas/versão final do layout disponíveis", key="home_layout")
                st.text_area("Notas de contexto", key="home_notes", height=70)

    if current_questionnaire is not None and st.session_state.replace_file:
        run_col, rerun_col = st.columns(2)
        run = run_col.button("Analisar ficheiro substituto", type="primary", width="stretch")
        rerun_current = rerun_col.button(
            "Reanalisar questionário atual", type="primary", width="stretch"
        )
    elif current_questionnaire is not None:
        run = False
        rerun_current = st.button(
            "Reanalisar questionário atual", type="primary", width="stretch"
        )
    else:
        run = st.button("Analisar questionário", type="primary", width="stretch")
        rerun_current = False
    if use_demo:
        demo = demo_questionnaire()
        metadata = QuestionnaireMetadata(
            title=demo.title,
            application_mode="Online autoaplicado",
            primary_device="Telemóvel",
            target_audience="Beneficiários de programas públicos",
            audience_profile="Público heterogéneo, com diferentes níveis de literacia digital e temática.",
            has_progress_indicator=False,
            automatic_routing=False,
            tested_on_device=False,
            layout_evidence_available=False,
        )
        analyse(demo, metadata, use_ai=False)
        st.session_state.analysis_source = "Exemplo demonstrativo"
        st.session_state.uploaded_file_bytes = None
        st.session_state.uploaded_file_name = "Exemplo demonstrativo integrado"
        st.session_state.custom_analysis_title = ""
        st.session_state.replace_file = False
        navigate("Questionário")
    if run:
        if uploaded is None:
            st.error("Carregue um ficheiro DOCX ou PDF, ou use o exemplo demonstrativo.")
            return
        file_format = Path(uploaded.name).suffix.removeprefix(".").upper() or "ficheiro"
        try:
            uploaded_bytes = uploaded.getvalue()
            questionnaire = parse_questionnaire(uploaded_bytes, uploaded.name)
        except QuestionnaireParseError as exc:
            parse_error = str(exc)
            st.error(f"Não foi possível ler o {file_format}: {parse_error}")
            if file_format == "PDF" and "texto selecionável" in parse_error.casefold():
                st.info(
                    "O PDF tem de conter texto selecionável. Esta versão não executa OCR "
                    "em documentos digitalizados ou compostos apenas por imagens."
                )
            return
        except Exception:
            st.error(
                f"Não foi possível ler o {file_format} devido a um erro inesperado. "
                "Confirme o ficheiro e tente novamente."
            )
            return
        metadata = metadata_from_form()
        custom_title = metadata.title.strip()
        if custom_title and custom_title != DEFAULT_ANALYSIS_TITLE:
            questionnaire.title = custom_title
            st.session_state.custom_analysis_title = custom_title
        else:
            metadata.title = questionnaire.title
            st.session_state.custom_analysis_title = ""
        analyse(questionnaire, metadata, use_ai=st.session_state.enable_ai)
        st.session_state.analysis_source = uploaded.name
        st.session_state.uploaded_file_bytes = uploaded_bytes
        st.session_state.uploaded_file_name = uploaded.name
        st.session_state.replace_file = False
        navigate("Questionário")
    if rerun_current:
        metadata = metadata_from_form()
        custom_title = metadata.title.strip()
        if custom_title and custom_title != DEFAULT_ANALYSIS_TITLE:
            current_questionnaire.title = custom_title
            st.session_state.custom_analysis_title = custom_title
        else:
            metadata.title = current_questionnaire.title
            st.session_state.custom_analysis_title = ""
        analyse(current_questionnaire, metadata, use_ai=st.session_state.enable_ai)
        navigate("Questionário")


def page_questionnaire() -> None:
    questionnaire = st.session_state.questionnaire
    if questionnaire is None:
        st.info("Comece por carregar um questionário.")
        return

    st.subheader("Questionário interpretado")
    back_button("Voltar a Carregar", "Carregar", "back-questionnaire-top")
    cols = st.columns(4)
    with cols[0]:
        kpi("Perguntas", len(questionnaire.questions), "elementos identificados")
    with cols[1]:
        kpi("Secções", len(questionnaire.sections), "blocos temáticos")
    with cols[2]:
        kpi("Escalas", sum(q.question_type == "escala" for q in questionnaire.questions), "perguntas de escala")
    with cols[3]:
        kpi("Filtros", sum(bool(q.routing_text) for q in questionnaire.questions), "routing detetado")

    for warning in questionnaire.parse_warnings:
        st.warning(warning)

    st.markdown("#### Confirme a extração")
    st.caption("Pode corrigir texto, secção e tipo antes de voltar a executar as regras.")
    frame = pd.DataFrame(
        [
            {
                "id": q.id,
                "rótulo": q.label,
                "secção": q.section,
                "pergunta": q.text,
                "tipo": q.question_type,
                "opções": " | ".join(q.options),
                "palavras": q.word_count,
                "origem": q.source,
            }
            for q in questionnaire.questions
        ]
    )
    edited = st.data_editor(
        frame,
        hide_index=True,
        width="stretch",
        disabled=["id", "palavras", "origem"],
        column_config={
            "pergunta": st.column_config.TextColumn(width="large"),
            "opções": st.column_config.TextColumn(width="large", help="Separe opções com |"),
        },
        key="question_editor",
    )
    col_back, col_save, col_next = st.columns([0.75, 1.25, 1])
    if col_back.button("← Voltar", key="back-questionnaire-bottom", width="stretch"):
        navigate("Carregar")
    if col_save.button("Guardar correções e repetir regras", width="stretch"):
        by_id = {question.id: question for question in questionnaire.questions}
        for row in edited.to_dict(orient="records"):
            question = by_id[row["id"]]
            question.label = str(row["rótulo"])
            question.section = str(row["secção"])
            question.text = str(row["pergunta"])
            question.question_type = str(row["tipo"])
            question.options = [value.strip() for value in str(row["opções"]).split("|") if value.strip()]
        reclassify_questions(questionnaire)
        st.session_state.findings = run_deterministic_review(questionnaire, st.session_state.metadata)
        st.session_state.ai_used = False
        st.success("Correções guardadas. As regras locais foram novamente executadas.")
    if col_next.button("Prosseguir para revisão", type="primary", width="stretch"):
        navigate("Revisão")


def _review_finding(finding: Finding, question_map: dict[str, object]) -> None:
    severity_css = severity_class(finding.effective_severity)
    method_css = "ai" if finding.method.startswith("IA") else ""
    header = f"{finding.criterion_id} · {finding.title} · {finding.effective_severity}"
    with st.expander(header, expanded=finding.effective_severity in {"Crítica", "Elevada"}):
        st.markdown(
            badge(finding.effective_severity, severity_css)
            + badge(f"Confiança {finding.confidence:.0%}")
            + badge(finding.method, method_css),
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="surv-question"><strong>{esc(finding.element_id)}</strong><br>{esc(finding.element_text)}</div>', unsafe_allow_html=True)
        col_evidence, col_reading = st.columns(2, gap="large")
        with col_evidence:
            st.markdown("**Evidência**")
            st.write(finding.evidence)
        with col_reading:
            st.markdown("**Leitura metodológica**")
            st.write(finding.explanation)
        st.markdown("**Recomendação proposta**")
        st.write(finding.recommendation)
        if finding.improved_wording:
            st.markdown("**✨ Proposta de reformulação**")
            st.success(finding.improved_wording)
        if finding.related_criteria:
            st.caption("Critérios relacionados: " + ", ".join(finding.related_criteria) + " — apresentados como ligação, não como alertas duplicados.")

        key = finding.finding_id
        left, middle, right = st.columns([0.85, 0.85, 1.8])
        decision = left.selectbox(
            "Decisão",
            DECISIONS,
            index=DECISIONS.index(finding.expert_decision),
            key=f"decision-{key}",
        )
        final_severity = middle.selectbox(
            "Gravidade final",
            SEVERITIES,
            index=SEVERITIES.index(finding.effective_severity),
            key=f"severity-{key}",
        )
        recommendation = right.text_area(
            "Recomendação final",
            value=finding.effective_recommendation,
            key=f"recommendation-{key}",
            height=92,
        )
        comment = st.text_area(
            "Justificação/comentário do avaliador",
            value=finding.expert_comment,
            key=f"comment-{key}",
            placeholder="Obrigatório quando altera ou rejeita a proposta.",
            height=75,
        )

        action_col, ai_col = st.columns([1, 1])
        if action_col.button("Guardar decisão", key=f"save-{key}", type="primary", width="stretch"):
            if decision in {"Modificar", "Rejeitar"} and not comment.strip():
                st.error("Registe uma justificação para modificar ou rejeitar a proposta.")
            else:
                finding.expert_decision = decision
                finding.expert_severity = final_severity
                finding.expert_recommendation = recommendation
                finding.expert_comment = comment
                st.success("Decisão guardada.")
        question = question_map.get(finding.element_id)
        can_rewrite = question is not None and bool(st.session_state.api_key)
        if ai_col.button(
            "✨ Melhorar esta pergunta",
            key=f"rewrite-{key}",
            disabled=not can_rewrite,
            width="stretch",
            help="Requer chave de API e nunca substitui automaticamente o original.",
        ):
            try:
                with st.spinner("A preparar uma reformulação…"):
                    rewrite = improve_question(
                        question,
                        finding,
                        st.session_state.metadata,
                        api_key=st.session_state.api_key,
                        model=st.session_state.model,
                    )
                finding.improved_wording = rewrite.improved_wording
                st.success(rewrite.improved_wording)
                st.caption(rewrite.reason)
            except Exception as exc:
                st.error(f"Não foi possível gerar a reformulação: {exc}")


def page_review() -> None:
    questionnaire = st.session_state.questionnaire
    findings: list[Finding] = st.session_state.findings
    if questionnaire is None:
        st.info("Comece por carregar um questionário.")
        return

    st.subheader("Revisão assistida")
    back_button("Voltar ao Questionário", "Questionário", "back-review-top")
    reviewed = sum(item.expert_decision != "Pendente" for item in findings)
    st.progress(reviewed / len(findings) if findings else 1.0, text=f"{reviewed}/{len(findings)} constatações revistas")

    filter_cols = st.columns(3)
    severity_filter = filter_cols[0].multiselect("Gravidade", SEVERITIES, default=SEVERITIES)
    decision_filter = filter_cols[1].multiselect("Decisão", DECISIONS, default=DECISIONS)
    criteria = sorted({finding.criterion_id for finding in findings})
    criterion_filter = filter_cols[2].multiselect("Critério", criteria, default=criteria)

    filtered = [
        item
        for item in findings
        if item.effective_severity in severity_filter
        and item.expert_decision in decision_filter
        and item.criterion_id in criterion_filter
    ]
    st.caption(f"A mostrar {len(filtered)} de {len(findings)} constatações. Nenhuma decisão é aplicada automaticamente.")
    question_map = {question.id: question for question in questionnaire.questions}
    for finding in filtered:
        _review_finding(finding, question_map)

    if not findings:
        st.success("As regras locais não geraram alertas. Complete a evidência e a validação antes de concluir que o critério é forte.")
    back_col, next_col = st.columns([1, 1])
    if back_col.button("← Voltar ao Questionário", key="back-review-bottom", width="stretch"):
        navigate("Questionário")
    if next_col.button("Ver síntese →", type="primary", width="stretch"):
        navigate("Síntese")


def page_summary() -> None:
    questionnaire = st.session_state.questionnaire
    findings: list[Finding] = st.session_state.findings
    if questionnaire is None:
        st.info("Comece por carregar um questionário.")
        return
    synthesis = synthesise(questionnaire, st.session_state.metadata, findings)
    st.subheader("Síntese metodológica")
    back_button("Voltar à Revisão", "Revisão", "back-summary-top")
    st.markdown(
        f'<div class="surv-synthesis"><div class="surv-eyebrow">ITEM D2.1.03 · {esc(synthesis.status)}</div>'
        f'<h2>{esc(synthesis.classification)}</h2><p>{esc(synthesis.rationale)}</p></div>',
        unsafe_allow_html=True,
    )
    columns = st.columns(4)
    with columns[0]:
        kpi("Validação", f"{synthesis.reviewed_findings}/{synthesis.total_findings}", "decisões registadas")
    with columns[1]:
        kpi("Elevadas/críticas", synthesis.proposed_counts["Elevada"] + synthesis.proposed_counts["Crítica"], "propostas ativas")
    with columns[2]:
        kpi("Evidência", "Completa" if synthesis.evidence_complete else "Parcial", "contexto + layout + teste")
    with columns[3]:
        kpi("Motor", "Híbrido" if st.session_state.ai_used else "Local", "IA usada" if st.session_state.ai_used else "regras explicáveis")

    chart_frame = pd.DataFrame(
        {
            "Gravidade": SEVERITIES,
            "Propostas ativas": [synthesis.proposed_counts[item] for item in SEVERITIES],
            "Confirmadas": [synthesis.confirmed_counts[item] for item in SEVERITIES],
        }
    ).set_index("Gravidade")
    st.markdown("#### Perfil das constatações")
    st.bar_chart(chart_frame, color=["#3592CF", "#34ABA2"], horizontal=True)

    st.markdown("#### Cobertura dos critérios P0")
    finding_criteria = Counter(finding.criterion_id for finding in findings)
    coverage = pd.DataFrame(
        [
            {
                "Critério": item["id"],
                "Item": item["item"],
                "Constatações": finding_criteria.get(item["id"], 0),
                "Estado": "Com evidência de alerta" if finding_criteria.get(item["id"]) else "Sem alerta automático / requer validação",
            }
            for item in p0_catalog()
        ]
    )
    st.dataframe(coverage, hide_index=True, width="stretch")

    active_priority = [
        finding
        for finding in findings
        if finding.expert_decision not in {"Rejeitar", "N.A."}
        and finding.effective_severity in {"Crítica", "Elevada"}
    ]
    if active_priority:
        st.markdown("#### Ações prioritárias")
        for index, finding in enumerate(active_priority[:5], start=1):
            st.markdown(f"**{index}. {finding.element_id} — {finding.title}**  \n{finding.effective_recommendation}")
    back_col, next_col = st.columns([1, 1])
    if back_col.button("← Voltar à Revisão", key="back-summary-bottom", width="stretch"):
        navigate("Revisão")
    if next_col.button("Preparar exportação →", type="primary", width="stretch"):
        navigate("Exportar")


def page_export() -> None:
    questionnaire = st.session_state.questionnaire
    findings: list[Finding] = st.session_state.findings
    if questionnaire is None:
        st.info("Comece por carregar um questionário.")
        return
    synthesis = synthesise(questionnaire, st.session_state.metadata, findings)
    st.subheader("Exportar avaliação")
    back_button("Voltar à Síntese", "Síntese", "back-export-top")
    pending = sum(finding.expert_decision == "Pendente" for finding in findings)
    if pending:
        st.warning(f"Existem {pending} constatações pendentes. Os ficheiros serão identificados como proposta preliminar.")
    else:
        st.success("Todas as constatações têm uma decisão pericial registada.")

    with st.container(border=True):
        st.markdown("#### Pacote de resultados")
        st.write("O relatório inclui rastreabilidade entre critério, regra, evidência, recomendação e decisão do avaliador.")
        filename_root = "SURV4IMPACT_Revisao_" + "_".join(questionnaire.title.split())[:45]
        col_word, col_excel, col_json = st.columns(3)
        col_word.download_button(
            "Descarregar relatório Word",
            data=export_docx(questionnaire, st.session_state.metadata, findings, synthesis),
            file_name=filename_root + ".docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
            width="stretch",
        )
        col_excel.download_button(
            "Descarregar grelha Excel",
            data=export_xlsx(questionnaire, st.session_state.metadata, findings, synthesis),
            file_name=filename_root + ".xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
        col_json.download_button(
            "Descarregar dados JSON",
            data=export_json(questionnaire, st.session_state.metadata, findings, synthesis),
            file_name=filename_root + ".json",
            mime="application/json",
            width="stretch",
        )

    with st.expander("Pré-visualizar a grelha de constatações"):
        st.dataframe(findings_dataframe(findings), hide_index=True, width="stretch")

    if st.button("← Voltar à Síntese", key="back-export-bottom", width="stretch"):
        navigate("Síntese")


def sidebar() -> None:
    with st.sidebar:
        st.markdown(
            '<div class="surv-sidebar-brand">SURV4IMPACT <span>AI</span></div>',
            unsafe_allow_html=True,
        )
        st.caption(f"Assistente de revisão metodológica · v{__version__}")
        selected = st.radio(
            "Fluxo",
            STAGES,
            index=STAGES.index(st.session_state.stage),
            label_visibility="collapsed",
        )
        if selected != st.session_state.stage:
            st.session_state.stage = selected
            st.rerun()
        st.divider()
        with st.expander("Configuração da IA", expanded=False):
            st.toggle("Ativar revisão semântica", key="enable_ai")
            st.text_input(
                "Chave da API",
                type="password",
                key="api_key",
                help="Mantida apenas na memória da sessão; pode também usar OPENAI_API_KEY.",
            )
            st.text_input("Modelo", key="model")
            st.caption("Sem chave, a aplicação continua a funcionar com regras locais.")
        st.divider()
        st.caption("15 critérios P0 · 20 regras detalhadas para D2.1.03 · validação pericial obrigatória")
        if st.session_state.questionnaire is not None:
            if st.button("Nova análise", width="stretch"):
                st.session_state.questionnaire = None
                st.session_state.findings = []
                st.session_state.analysis_source = ""
                st.session_state.uploaded_file_bytes = None
                st.session_state.uploaded_file_name = ""
                st.session_state.custom_analysis_title = ""
                st.session_state.metadata = QuestionnaireMetadata()
                st.session_state.ai_used = False
                st.session_state.replace_file = False
                st.session_state.upload_generation += 1
                for key in list(st.session_state):
                    if key.startswith("home_"):
                        del st.session_state[key]
                st.session_state.stage = "Carregar"
                st.rerun()


init_state()
sidebar()
brand_system()
hero()
stepper()

{
    "Carregar": page_upload,
    "Leitura do Questionário": page_questionnaire,
    "Análise": page_review,
    "Síntese": page_summary,
    "Exportar Relatório": page_export,
}[st.session_state.stage]()
