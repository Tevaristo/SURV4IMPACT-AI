from surv4impact.demo import demo_questionnaire
from surv4impact.models import QuestionnaireMetadata
from surv4impact.rules import run_deterministic_review
from surv4impact.synthesis import synthesise


def test_missing_mode_blocks_synthesis():
    questionnaire = demo_questionnaire()
    metadata = QuestionnaireMetadata(target_audience="Beneficiários", audience_profile="Heterogéneo")
    findings = run_deterministic_review(questionnaire, metadata)

    assert any(item.rule_id == "D2.1.03-META-01" for item in findings)
    assert synthesise(questionnaire, metadata, findings).classification == "Não evidenciado"


def test_demo_detects_routing_and_double_negative():
    questionnaire = demo_questionnaire()
    metadata = QuestionnaireMetadata(
        application_mode="Online autoaplicado",
        primary_device="Telemóvel",
        target_audience="Beneficiários",
        audience_profile="Público heterogéneo",
        automatic_routing=False,
        tested_on_device=False,
    )
    findings = run_deterministic_review(questionnaire, metadata)
    rules = {item.rule_id for item in findings}

    assert "D2.1.03-WEB-03" in rules
    assert "D2.3.03-RULE-NEG" in rules
    assert synthesise(questionnaire, metadata, findings).status == "Proposta preliminar"


def test_rejected_findings_do_not_count_as_confirmed():
    questionnaire = demo_questionnaire()
    metadata = QuestionnaireMetadata(
        application_mode="Papel autoaplicado",
        primary_device="Papel",
        target_audience="Especialistas",
        audience_profile="Elevada literacia temática",
        layout_evidence_available=True,
    )
    findings = run_deterministic_review(questionnaire, metadata)
    for finding in findings:
        finding.expert_decision = "Rejeitar"
        finding.expert_comment = "Não aplicável ao contexto documentado."

    synthesis = synthesise(questionnaire, metadata, findings)
    assert synthesis.status == "Validada pelo avaliador"
    assert sum(synthesis.confirmed_counts.values()) == 0

