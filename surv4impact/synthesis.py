from __future__ import annotations

from collections import Counter

from .models import Finding, Questionnaire, QuestionnaireMetadata, Synthesis


COUNTED_DECISIONS = {"Aceitar", "Modificar"}


def _counts(findings: list[Finding], confirmed_only: bool) -> dict[str, int]:
    selected = []
    for finding in findings:
        if finding.expert_decision in {"Rejeitar", "N.A."}:
            continue
        if confirmed_only and finding.expert_decision not in COUNTED_DECISIONS:
            continue
        selected.append(finding.effective_severity)
    counts = Counter(selected)
    return {
        name: counts.get(name, 0)
        for name in ("Crítica", "Elevada", "Moderada", "Baixa", "Informativa")
    }


def synthesise(
    questionnaire: Questionnaire,
    metadata: QuestionnaireMetadata,
    findings: list[Finding],
) -> Synthesis:
    confirmed = _counts(findings, confirmed_only=True)
    proposed = _counts(findings, confirmed_only=False)
    reviewed = sum(f.expert_decision != "Pendente" for f in findings)
    evidence_complete = bool(
        questionnaire.questions
        and metadata.application_mode
        and metadata.target_audience
        and metadata.audience_profile
        and metadata.layout_evidence_available
        and (metadata.tested_on_device is True or "papel" in metadata.application_mode.casefold())
    )

    status = "Validada pelo avaliador" if reviewed == len(findings) else "Proposta preliminar"
    active = confirmed if reviewed == len(findings) else proposed

    if not questionnaire.questions or not metadata.application_mode:
        classification = "Não evidenciado"
        rationale = (
            "O modo de aplicação e uma estrutura de perguntas identificável são condições de entrada "
            "para avaliar a coerência entre desenho e modo."
        )
    elif active["Crítica"] >= 1 or active["Elevada"] >= 2:
        classification = "Com limitações"
        rationale = "Existe pelo menos um problema crítico ou dois problemas elevados com potencial impacto material."
    elif active["Elevada"] >= 1 or active["Moderada"] >= 3:
        classification = "Intermédio"
        rationale = "A coerência global é plausível, mas subsiste uma fragilidade elevada ou várias limitações moderadas."
    elif active["Moderada"] + active["Baixa"] in {1, 2}:
        classification = "Intermédio a forte"
        rationale = "Foram identificadas apenas reservas pontuais, ainda sujeitas à validação do contexto e do layout."
    elif sum(active.values()) == active["Informativa"] and evidence_complete:
        classification = "Forte"
        rationale = "Não existem problemas substantivos confirmados e a evidência cobre público, modo, layout e teste."
    else:
        classification = "Intermédio"
        rationale = (
            "A ausência de alertas não demonstra, por si só, uma adequação forte; falta completar ou validar evidência."
        )

    if status == "Proposta preliminar":
        rationale += " A classificação usa alertas ainda pendentes e deve ser confirmada pelo avaliador."

    return Synthesis(
        classification=classification,
        status=status,
        rationale=rationale,
        confirmed_counts=confirmed,
        proposed_counts=proposed,
        evidence_complete=evidence_complete,
        reviewed_findings=reviewed,
        total_findings=len(findings),
    )

