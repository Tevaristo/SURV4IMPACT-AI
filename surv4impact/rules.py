from __future__ import annotations

import hashlib
import re
from collections import Counter
from difflib import SequenceMatcher

from .knowledge import load_pilot_rules
from .models import Finding, Questionnaire, QuestionnaireMetadata, Question


SEVERITY_ORDER = {
    "Crítica": 5,
    "Elevada": 4,
    "Moderada": 3,
    "Baixa": 2,
    "Informativa": 1,
}

PERIOD_RE = re.compile(
    r"\b(?:últim[oa]s?|nos últimos|desde|durante|entre|por semana|por mês|por ano|"
    r"diariamente|semanalmente|mensalmente|anualmente|atualmente|hoje|ontem|\d{4})\b",
    re.IGNORECASE,
)
BEHAVIOUR_RE = re.compile(
    r"\b(?:utiliz|particip|receb|recorr|contact|frequência|vezes|satisfeit|avali|experiência|apoio)\w*\b",
    re.IGNORECASE,
)
DOUBLE_NEGATIVE_RE = re.compile(
    r"\b(?:não|nunca|nenhum[ao]?|sem)\b.*\b(?:não|nunca|nenhum[ao]?|sem)\b",
    re.IGNORECASE,
)
LEADING_RE = re.compile(
    r"\b(?:não acha|não considera|certamente|evidentemente|obviamente|felizmente|"
    r"concorda que|será que não|como sabe)\b",
    re.IGNORECASE,
)
ROUTING_TARGET_RE = re.compile(r"(?:pergunta|questão|q)\s*(\d{1,3})", re.IGNORECASE)
ACRONYM_RE = re.compile(r"\b[A-ZÁÉÍÓÚÇ]{3,}(?:\d+)?\b")


def _rule_map() -> dict[str, dict[str, str]]:
    return {rule["rule_id"]: rule for rule in load_pilot_rules()}


def _stable_id(rule_id: str, element_id: str, evidence: str) -> str:
    digest = hashlib.sha1(f"{rule_id}|{element_id}|{evidence}".encode("utf-8")).hexdigest()[:9]
    return f"F-{digest}"


def _severity(value: str, fallback: str = "Moderada") -> str:
    for candidate in SEVERITY_ORDER:
        if candidate.lower() in value.lower():
            return candidate
    return fallback


def _finding(
    *,
    rule_id: str,
    criterion_id: str,
    element_id: str,
    element_text: str,
    title: str,
    severity: str,
    confidence: float,
    evidence: str,
    explanation: str,
    recommendation: str,
    method: str,
    source: str = "",
    component: str = "",
    related_criteria: list[str] | None = None,
    finding_type: str = "potencial_problema",
) -> Finding:
    return Finding(
        finding_id=_stable_id(rule_id, element_id, evidence),
        criterion_id=criterion_id,
        rule_id=rule_id,
        element_id=element_id,
        element_text=element_text,
        title=title,
        finding_type=finding_type,
        severity=severity,
        confidence=confidence,
        evidence=evidence,
        explanation=explanation,
        recommendation=recommendation,
        method=method,
        source=source,
        component=component,
        related_criteria=related_criteria or [],
    )


def _matrix_finding(
    rule_id: str,
    *,
    element_id: str,
    element_text: str,
    title: str,
    evidence: str,
    confidence: float,
    source: str = "",
    severity: str | None = None,
    related_criteria: list[str] | None = None,
    finding_type: str = "potencial_problema",
) -> Finding:
    rule = _rule_map()[rule_id]
    return _finding(
        rule_id=rule_id,
        criterion_id="D2.1.03",
        element_id=element_id,
        element_text=element_text,
        title=title,
        severity=severity or _severity(rule.get("severity", "")),
        confidence=confidence,
        evidence=evidence,
        explanation=rule.get("explanation", ""),
        recommendation=rule.get("recommendation", ""),
        method=rule.get("method", "Regra"),
        source=source,
        component=rule.get("component", ""),
        related_criteria=related_criteria,
        finding_type=finding_type,
    )


def _mode_flags(metadata: QuestionnaireMetadata) -> tuple[bool, bool, bool, bool]:
    mode = metadata.application_mode.casefold()
    device = metadata.primary_device.casefold()
    oral = "telef" in mode or "entrevista" in mode or "assistid" in mode
    online = "online" in mode or "web" in mode
    paper = "papel" in mode
    mobile = "telem" in device or "tablet" in device
    return oral, online, paper, mobile


def _technical_acronyms(question: Question) -> list[str]:
    ignored = {"SIM", "NÃO", "NA", "NS", "NR", "UE", "IVA"}
    return sorted({item for item in ACRONYM_RE.findall(question.text) if item not in ignored})


def _scale_direction(options: list[str]) -> str:
    if not options:
        return ""
    positive = re.compile(r"(?:muito positivo|excelente|totalmente satisfeit|concordo totalmente)", re.I)
    negative = re.compile(r"(?:muito negativo|péssim|totalmente insatisfeit|discordo totalmente)", re.I)
    if positive.search(options[0]) or negative.search(options[-1]):
        return "positivo-negativo"
    if negative.search(options[0]) or positive.search(options[-1]):
        return "negativo-positivo"
    return ""


def _question_length_finding(question: Question, limit: int, mode_label: str) -> Finding:
    return _matrix_finding(
        "D2.1.03-COMP-01",
        element_id=question.id,
        element_text=question.text,
        title="Pergunta potencialmente extensa para o modo",
        evidence=f"{question.word_count} palavras; limiar de triagem: {limit}; modo: {mode_label or 'não confirmado'}.",
        confidence=0.72,
        source=question.source,
        related_criteria=["D2.3.01", "D2.6.02"],
    )


def run_deterministic_review(
    questionnaire: Questionnaire, metadata: QuestionnaireMetadata
) -> list[Finding]:
    findings: list[Finding] = []
    oral, online, paper, mobile = _mode_flags(metadata)

    if not metadata.application_mode:
        findings.append(
            _matrix_finding(
                "D2.1.03-META-01",
                element_id="questionnaire",
                element_text=questionnaire.title,
                title="Modo de aplicação não confirmado",
                evidence="O campo ‘modo de aplicação’ não foi preenchido.",
                confidence=0.99,
                finding_type="evidencia_insuficiente",
            )
        )

    if not metadata.target_audience or not metadata.audience_profile:
        missing = []
        if not metadata.target_audience:
            missing.append("público-alvo")
        if not metadata.audience_profile:
            missing.append("perfil de literacia/familiaridade")
        findings.append(
            _matrix_finding(
                "D2.1.03-META-02",
                element_id="audience",
                element_text=metadata.target_audience or "Público não descrito",
                title="Perfil do público incompleto",
                evidence="Campos em falta: " + ", ".join(missing) + ".",
                confidence=0.98,
                finding_type="evidencia_insuficiente",
                related_criteria=["D2.3.02", "D2.6.02"],
            )
        )

    length_limit = 25 if oral else 35
    mode_label = metadata.application_mode
    for question in questionnaire.questions:
        if question.word_count > length_limit:
            findings.append(_question_length_finding(question, length_limit, mode_label))

        clause_markers = len(re.findall(r"\b(?:que|quando|caso|sempre que|desde que|se)\b", question.text, re.I))
        if clause_markers >= 3 or (question.text.count(",") >= 3 and question.word_count > 22):
            findings.append(
                _matrix_finding(
                    "D2.1.03-COMP-02",
                    element_id=question.id,
                    element_text=question.text,
                    title="Sintaxe potencialmente complexa",
                    evidence=f"Foram detetados {clause_markers} marcadores condicionais/subordinativos e {question.text.count(',')} vírgulas.",
                    confidence=0.63,
                    source=question.source,
                    related_criteria=["D2.3.01", "D2.6.02"],
                )
            )

        acronyms = _technical_acronyms(question)
        general_public = any(
            term in metadata.audience_profile.casefold()
            for term in ("geral", "heterog", "baixa", "não especial", "divers")
        )
        if acronyms and general_public:
            findings.append(
                _matrix_finding(
                    "D2.1.03-COMP-03",
                    element_id=question.id,
                    element_text=question.text,
                    title="Siglas ou linguagem técnica podem dificultar a compreensão",
                    evidence="Siglas detetadas: " + ", ".join(acronyms) + ".",
                    confidence=0.68,
                    source=question.source,
                    related_criteria=["D2.3.02", "D2.3.03"],
                )
            )

        if oral and len(question.options) > 7:
            findings.append(
                _matrix_finding(
                    "D2.1.03-ORAL-01",
                    element_id=question.id,
                    element_text=question.text,
                    title="Demasiadas opções para apresentação oral",
                    evidence=f"{len(question.options)} opções de resposta no modo {metadata.application_mode}.",
                    confidence=0.88,
                    source=question.source,
                    related_criteria=["D2.2.06", "D2.6.02"],
                )
            )

        if oral and question.question_type == "grelha/matriz":
            findings.append(
                _matrix_finding(
                    "D2.1.03-ORAL-02",
                    element_id=question.id,
                    element_text=question.text,
                    title="Grelha incompatível com uma tarefa exclusivamente oral",
                    evidence=f"Grelha com {question.matrix_rows} linhas e {question.matrix_columns} colunas.",
                    confidence=0.9,
                    source=question.source,
                    related_criteria=["D2.2.06", "D2.6.02"],
                )
            )

        if (online or mobile) and question.question_type == "grelha/matriz" and (
            question.matrix_rows > 5 or question.matrix_columns > 5
        ):
            findings.append(
                _matrix_finding(
                    "D2.1.03-WEB-01",
                    element_id=question.id,
                    element_text=question.text,
                    title="Grelha extensa para apresentação em ecrã",
                    evidence=f"{question.matrix_rows} linhas × {question.matrix_columns} colunas; dispositivo: {metadata.primary_device or 'não indicado'}.",
                    confidence=0.81,
                    source=question.source,
                    related_criteria=["D2.2.06", "D2.6.02"],
                )
            )

        if online and question.routing_text and metadata.automatic_routing is not True:
            findings.append(
                _matrix_finding(
                    "D2.1.03-WEB-03",
                    element_id=question.id,
                    element_text=question.text,
                    title="Encaminhamento manual num questionário online",
                    evidence=question.routing_text,
                    confidence=0.86 if metadata.automatic_routing is False else 0.62,
                    source=question.source,
                    related_criteria=["D2.2.07", "D2.6.01"],
                )
            )

        if paper and question.min_font_pt is not None and question.min_font_pt < 10:
            findings.append(
                _matrix_finding(
                    "D2.1.03-PAPER-02",
                    element_id=question.id,
                    element_text=question.text,
                    title="Tamanho de letra reduzido",
                    evidence=f"Tamanho mínimo detetado: {question.min_font_pt:.1f} pt.",
                    confidence=0.91,
                    source=question.source,
                    related_criteria=["D2.3.06"],
                )
            )

        if DOUBLE_NEGATIVE_RE.search(question.text):
            findings.append(
                _finding(
                    rule_id="D2.3.03-RULE-NEG",
                    criterion_id="D2.3.03",
                    element_id=question.id,
                    element_text=question.text,
                    title="Possível dupla negação",
                    severity="Elevada",
                    confidence=0.86,
                    evidence=DOUBLE_NEGATIVE_RE.search(question.text).group(0),
                    explanation="A combinação de negações aumenta o risco de interpretação e codificação invertidas.",
                    recommendation="Reformular a pergunta pela positiva e manter uma única tarefa de resposta.",
                    method="Regra linguística",
                    source=question.source,
                    related_criteria=["D2.3.01"],
                )
            )
        elif LEADING_RE.search(question.text):
            findings.append(
                _finding(
                    rule_id="D2.3.03-RULE-LEAD",
                    criterion_id="D2.3.03",
                    element_id=question.id,
                    element_text=question.text,
                    title="Formulação potencialmente indutora",
                    severity="Elevada",
                    confidence=0.74,
                    evidence=LEADING_RE.search(question.text).group(0),
                    explanation="A formulação sugere uma resposta ou enquadra a questão de forma assimétrica.",
                    recommendation="Usar uma formulação neutra que não indique a resposta socialmente ou institucionalmente esperada.",
                    method="Regra linguística",
                    source=question.source,
                )
            )

        if BEHAVIOUR_RE.search(question.text) and not PERIOD_RE.search(question.text):
            findings.append(
                _finding(
                    rule_id="D2.3.05-RULE-PERIOD",
                    criterion_id="D2.3.05",
                    element_id=question.id,
                    element_text=question.text,
                    title="Período de referência possivelmente ausente",
                    severity="Moderada",
                    confidence=0.65,
                    evidence="A pergunta refere uma experiência/comportamento sem expressão temporal explícita.",
                    explanation="Respondentes podem considerar períodos diferentes, reduzindo a comparabilidade das respostas.",
                    recommendation="Indicar um período coerente com o fenómeno, por exemplo ‘nos últimos 12 meses’.",
                    method="Regra linguística",
                    source=question.source,
                )
            )

    if online and len(questionnaire.questions) > 25 and metadata.has_progress_indicator is not True:
        findings.append(
            _matrix_finding(
                "D2.1.03-WEB-02",
                element_id="questionnaire",
                element_text=questionnaire.title,
                title="Questionário online extenso sem indicador de progresso confirmado",
                evidence=f"{len(questionnaire.questions)} perguntas; indicador de progresso: {metadata.has_progress_indicator}.",
                confidence=0.78 if metadata.has_progress_indicator is False else 0.58,
                related_criteria=["D2.6.01", "D2.6.02"],
            )
        )

    if mobile and metadata.tested_on_device is not True:
        findings.append(
            _matrix_finding(
                "D2.1.03-WEB-04",
                element_id="questionnaire",
                element_text=questionnaire.title,
                title="Teste no dispositivo móvel não confirmado",
                evidence=f"Dispositivo principal: {metadata.primary_device}; teste confirmado: {metadata.tested_on_device}.",
                confidence=0.9 if metadata.tested_on_device is False else 0.65,
                finding_type="evidencia_insuficiente" if metadata.tested_on_device is None else "potencial_problema",
            )
        )

    if paper:
        known_numbers = {re.sub(r"\D", "", question.label) for question in questionnaire.questions}
        for question in questionnaire.questions:
            for target in ROUTING_TARGET_RE.findall(question.routing_text):
                if target not in known_numbers:
                    findings.append(
                        _matrix_finding(
                            "D2.1.03-PAPER-01",
                            element_id=question.id,
                            element_text=question.text,
                            title="Destino de encaminhamento não identificado",
                            evidence=f"A instrução remete para a pergunta {target}, que não foi identificada no questionário.",
                            confidence=0.91,
                            source=question.source,
                            related_criteria=["D2.2.07", "D2.6.01"],
                        )
                    )

    consecutive_types = []
    for question in questionnaire.questions:
        if consecutive_types and consecutive_types[-1][0] == question.question_type:
            consecutive_types[-1][1] += 1
        else:
            consecutive_types.append([question.question_type, 1])
    for question_type, count in consecutive_types:
        if count > 10:
            findings.append(
                _matrix_finding(
                    "D2.1.03-STRUCT-01",
                    element_id="questionnaire",
                    element_text=questionnaire.title,
                    title="Bloco repetitivo potencialmente fatigante",
                    evidence=f"Sequência de {count} perguntas do tipo ‘{question_type}’.",
                    confidence=0.71,
                    related_criteria=["D2.2.02", "D2.6.01", "D2.6.02"],
                )
            )

    open_questions = [q for q in questionnaire.questions if q.question_type == "aberta"]
    mandatory_open = [q for q in open_questions if q.required]
    if len(open_questions) > 5 or len(mandatory_open) > 2:
        findings.append(
            _matrix_finding(
                "D2.1.03-OPEN-01",
                element_id="questionnaire",
                element_text=questionnaire.title,
                title="Carga elevada de resposta aberta",
                evidence=f"{len(open_questions)} perguntas abertas, das quais {len(mandatory_open)} assinaladas como obrigatórias.",
                confidence=0.75,
                severity="Elevada" if len(mandatory_open) > 3 else "Moderada",
                related_criteria=["D2.5.01", "D2.6.02"],
            )
        )

    if not questionnaire.instructions:
        findings.append(
            _matrix_finding(
                "D2.1.03-SELF-01",
                element_id="questionnaire",
                element_text=questionnaire.title,
                title="Instruções de preenchimento não identificadas",
                evidence="O extrator não identificou texto introdutório ou instruções autónomas.",
                confidence=0.7,
                finding_type="evidencia_insuficiente",
                related_criteria=["D2.3.06", "D2.6.01"],
            )
        )

    if metadata.accessibility_needs and not metadata.accommodations:
        findings.append(
            _matrix_finding(
                "D2.1.03-ACCESS-01",
                element_id="audience",
                element_text=metadata.accessibility_needs,
                title="Necessidades de acessibilidade sem adaptação documentada",
                evidence=f"Necessidades: {metadata.accessibility_needs}; adaptações: não indicadas.",
                confidence=0.91,
                severity="Elevada",
                related_criteria=["D2.3.02", "D2.6.02"],
            )
        )

    if not metadata.layout_evidence_available:
        findings.append(
            _matrix_finding(
                "D2.1.03-LAYOUT-01",
                element_id="questionnaire",
                element_text=questionnaire.title,
                title="Layout final ainda requer validação visual",
                evidence="Não foi confirmada a disponibilidade de capturas ou da versão final no dispositivo.",
                confidence=0.95,
                severity="Informativa",
                finding_type="evidencia_insuficiente",
            )
        )

    if len(questionnaire.questions) > 10 and len(questionnaire.sections) <= 1:
        findings.append(
            _finding(
                rule_id="D2.2.01-RULE-SECTIONS",
                criterion_id="D2.2.01",
                element_id="questionnaire",
                element_text=questionnaire.title,
                title="Organização temática pouco visível",
                severity="Moderada",
                confidence=0.69,
                evidence=f"{len(questionnaire.questions)} perguntas e {len(questionnaire.sections)} secção identificada.",
                explanation="A ausência de blocos visíveis pode dificultar a orientação e aumentar a sensação de extensão.",
                recommendation="Agrupar itens relacionados e usar títulos de secção informativos.",
                method="Regra estrutural",
                related_criteria=["D2.6.01"],
            )
        )

    scale_questions = [q for q in questionnaire.questions if q.question_type == "escala"]
    signatures = Counter(len(q.options) for q in scale_questions if q.options)
    directions = Counter(_scale_direction(q.options) for q in scale_questions)
    directions.pop("", None)
    if len(signatures) > 1 or len(directions) > 1:
        details = ", ".join(f"{points} pontos: {count}" for points, count in signatures.items())
        findings.append(
            _finding(
                rule_id="D2.2.06-RULE-SCALE",
                criterion_id="D2.2.06",
                element_id="questionnaire",
                element_text=questionnaire.title,
                title="Formatos ou direção das escalas variam",
                severity="Elevada" if len(directions) > 1 else "Moderada",
                confidence=0.83,
                evidence=f"Escalas identificadas — {details or 'sem contagem'}; direções: {dict(directions)}.",
                explanation="Alterações não justificadas no número de pontos ou na direção aumentam erros de resposta e reduzem comparabilidade.",
                recommendation="Uniformizar escalas equivalentes ou explicar claramente cada mudança necessária.",
                method="Regra estrutural",
                related_criteria=["D2.3.04"],
            )
        )

    for first_index, first in enumerate(questionnaire.questions):
        first_text = re.sub(r"\W+", " ", first.text.casefold()).strip()
        if len(first_text) < 20:
            continue
        for second in questionnaire.questions[first_index + 1 :]:
            second_text = re.sub(r"\W+", " ", second.text.casefold()).strip()
            ratio = SequenceMatcher(None, first_text, second_text).ratio()
            if ratio >= 0.92:
                findings.append(
                    _finding(
                        rule_id="D2.6.03-RULE-DUP",
                        criterion_id="D2.6.03",
                        element_id=second.id,
                        element_text=second.text,
                        title="Perguntas potencialmente redundantes",
                        severity="Moderada",
                        confidence=ratio,
                        evidence=f"Semelhança de {ratio:.0%} entre {first.label} e {second.label}.",
                        explanation="Itens quase duplicados aumentam a extensão sem acrescentar necessariamente informação.",
                        recommendation="Confirmar se os itens medem dimensões distintas; eliminar ou consolidar quando não acrescentam valor.",
                        method="Similaridade textual",
                        source=second.source,
                    )
                )

    unique: dict[str, Finding] = {}
    for finding in findings:
        unique.setdefault(finding.finding_id, finding)
    return sorted(
        unique.values(),
        key=lambda item: (-SEVERITY_ORDER.get(item.severity, 0), item.criterion_id, item.element_id),
    )

