"""Os 13 testes reais são opcionais no pytest local, mas gate obrigatório da qualificação.
Sem chave ficam NÃO EXECUTADOS; os testes técnicos não substituem esta bateria.
"""
import json
import os
import pytest
from prototipo.api import configuration, structured
from prototipo.models import Strict, ReviewBatch
from prototipo.engine import review_criterion
from prototipo.norma import load_norma, ROOT
from prototipo.state import new_session, replace_document, save_representation
from prototipo.extraction import from_text
from .cases import cases, APPROVED, PROVISIONAL


class PropositionResult(Strict):
    proposicao: str
    satisfeita: bool
    evidencia_na_resposta: str
    justificacao: str


class Evaluation(Strict):
    obrigatorias: list[PropositionResult]
    proibidas_ausentes: list[PropositionResult]
    acao_estado_limites_conformes: bool
    classificacao_integral_ausente: bool
    conclusao: str


@pytest.mark.parametrize("code", APPROVED + PROVISIONAL)
def test_case_input_provenance_and_status(code):
    case = cases()[code]
    assert case["input"] and case["expectativas"] and len(case["sha256"]) == 64
    assert (case["estatuto"] == "Aprovado") == (code in APPROVED)
    assert "### C." not in case["input"]
    assert "### D." not in case["input"]


@pytest.mark.parametrize("code", APPROVED + PROVISIONAL)
def test_live_methodological_propositions(code):
    key, model = configuration()
    if os.environ.get("PROTOTIPO_LIVE_TESTS") != "1" or not key:
        pytest.skip("Não executado: requer PROTOTIPO_LIVE_TESTS=1 e API configurada; não substituído por simulação.")
    case = cases()[code]
    n = load_norma()
    selected = case["regras"] or (["D2.6-R08"] if code.startswith("CT-12") else ["D2.4-R03"])
    s = new_session()
    inst, elements = from_text(case["input"], code + " — entrada B V11")
    replace_document(s, inst, elements)
    save_representation(s, elements, True)
    s["ambito"] = "recorte localizado"
    # Só B do próprio caso entra na análise; C/D entram exclusivamente no avaliador de QA.
    for criterion in sorted(set(r[:4] for r in selected)):
        review_criterion(s, criterion, key, model, only_rules=selected)
    result = ReviewBatch.model_validate({"verificacoes": list(s["verificacoes"].values())})
    judge = structured(key, model,
        "Avalia a conformidade semântica desta resposta com TODAS as proposições e campos das condições C/D. Aceita paráfrases. Não altera expectativas. Enumera todas as obrigatórias e todas as proibidas como proposições verificadas. A ausência de proibição deve ser explicitada. Não confundas verificação localizada com classificação integral. Esta é uma avaliação automática de QA, sujeita a revisão humana.",
        {"entrada": case["input"], "expectativas_C_D": case["expectativas"], "resposta": result.model_dump()}, Evaluation)
    folder = ROOT / "outputs/prototipo_testes_metodologicos"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (code + ".json")).write_text(json.dumps({"caso": case, "resposta": result.model_dump(), "avaliacao_automatica": judge.model_dump(), "modelo": model, "validacao_humana": "Por realizar"}, ensure_ascii=False, indent=2), encoding="utf-8")
    assert judge.obrigatorias and judge.proibidas_ausentes
    assert all(p.satisfeita for p in judge.obrigatorias + judge.proibidas_ausentes), judge.conclusao
    assert judge.acao_estado_limites_conformes and judge.classificacao_integral_ausente
