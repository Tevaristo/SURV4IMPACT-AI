from __future__ import annotations

import json
from typing import Iterable

from .knowledge import p0_catalog
from .models import (
    AISemanticReview,
    AIRewrite,
    Finding,
    Questionnaire,
    QuestionnaireMetadata,
    Question,
)


SEMANTIC_CRITERIA = {
    "D2.1.03",
    "D2.2.02",
    "D2.3.01",
    "D2.3.02",
    "D2.3.03",
    "D2.3.04",
    "D2.3.05",
    "D2.3.06",
    "D2.5.01",
    "D2.6.01",
    "D2.6.02",
    "D2.6.03",
}


def _client(api_key: str):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "A biblioteca openai não está instalada. Execute pip install -r requirements.txt."
        ) from exc
    return OpenAI(api_key=api_key)


def _criteria_context() -> str:
    rows = []
    for item in p0_catalog():
        if item["id"] in SEMANTIC_CRITERIA:
            rows.append(
                {
                    "id": item["id"],
                    "item": item["item"],
                    "pergunta_operacional": item.get("operational_question", ""),
                    "evidencia": item.get("evidence", ""),
                }
            )
    return json.dumps(rows, ensure_ascii=False)


def _chunks(items: list[Question], size: int = 20) -> Iterable[list[Question]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def run_ai_review(
    questionnaire: Questionnaire,
    metadata: QuestionnaireMetadata,
    *,
    api_key: str,
    model: str = "gpt-5.6",
) -> list[Finding]:
    if not api_key:
        raise ValueError("É necessária uma chave da API para executar a revisão semântica.")

    client = _client(api_key)
    results: list[Finding] = []
    criteria = _criteria_context()

    instructions = f"""
És um assistente metodológico especializado em desenho de questionários para avaliação de políticas públicas.
Analisa apenas segundo os critérios SURV4IMPACT fornecidos. A tua saída é uma proposta sujeita a validação pericial.

Regras obrigatórias:
- escreve em português europeu;
- não inventes contexto nem evidência;
- cita na evidência o segmento exato da pergunta que sustenta o alerta;
- usa ‘evidencia_insuficiente’ quando a decisão depender de contexto não fornecido;
- não transformes uma mera possibilidade abstrata num problema;
- distingue impacto metodológico de preferência estilística;
- associa cada alerta a um critério principal e, se necessário, a critérios relacionados;
- produz no máximo dois alertas por pergunta e evita duplicações;
- se não existir um problema material, devolve ‘sem_problema’;
- a reformulação deve preservar a intenção aparente; se essa intenção for incerta, deixa improved_wording vazio.

Critérios aplicáveis:
{criteria}
""".strip()

    for batch in _chunks(questionnaire.questions):
        payload = {
            "contexto": metadata.to_dict(),
            "questionario": questionnaire.title,
            "perguntas": [
                {
                    "question_id": q.id,
                    "label": q.label,
                    "section": q.section,
                    "text": q.text,
                    "options": q.options,
                    "type": q.question_type,
                    "routing": q.routing_text,
                }
                for q in batch
            ],
        }
        response = client.responses.parse(
            model=model,
            input=[
                {"role": "developer", "content": instructions},
                {
                    "role": "user",
                    "content": "Avalia este lote de perguntas:\n" + json.dumps(payload, ensure_ascii=False),
                },
            ],
            text_format=AISemanticReview,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("A resposta de IA não pôde ser convertida para o formato esperado.")

        question_map = {question.id: question for question in batch}
        for item in parsed.findings:
            if item.assessment == "sem_problema":
                continue
            question = question_map.get(item.question_id)
            if question is None:
                continue
            finding_type = (
                "evidencia_insuficiente"
                if item.assessment == "evidencia_insuficiente"
                else "potencial_problema"
            )
            results.append(
                Finding(
                    finding_id=f"AI-{item.criterion_id}-{question.id}-{len(results) + 1}",
                    criterion_id=item.criterion_id,
                    rule_id=f"{item.criterion_id}-AI",
                    element_id=question.id,
                    element_text=question.text,
                    title=item.title,
                    finding_type=finding_type,
                    severity=item.severity,
                    confidence=item.confidence,
                    evidence=item.evidence,
                    explanation=item.explanation,
                    recommendation=item.recommendation,
                    method="IA semântica — proposta",
                    source=question.source,
                    component="Revisão semântica",
                    related_criteria=item.related_criteria,
                    improved_wording=item.improved_wording,
                )
            )
    return results


def improve_question(
    question: Question,
    finding: Finding,
    metadata: QuestionnaireMetadata,
    *,
    api_key: str,
    model: str = "gpt-5.6",
) -> AIRewrite:
    client = _client(api_key)
    prompt = {
        "pergunta": question.text,
        "opcoes": question.options,
        "problema": finding.title,
        "explicacao": finding.explanation,
        "recomendacao": finding.effective_recommendation,
        "publico": metadata.target_audience,
        "perfil": metadata.audience_profile,
        "modo": metadata.application_mode,
    }
    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "developer",
                "content": (
                    "Reformula a pergunta em português europeu, preservando a intenção aparente, "
                    "corrigindo apenas o problema identificado. Não inventes informação substantiva. "
                    "Explica sucintamente a alteração e, quando útil, dá até duas alternativas."
                ),
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        text_format=AIRewrite,
    )
    if response.output_parsed is None:
        raise RuntimeError("Não foi possível obter uma reformulação estruturada.")
    return response.output_parsed
