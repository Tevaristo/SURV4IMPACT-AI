from surv4impact.demo import demo_questionnaire
from surv4impact.models import QuestionnaireMetadata
from surv4impact.reporting import export_docx, export_json, export_xlsx
from surv4impact.rules import run_deterministic_review
from surv4impact.synthesis import synthesise


def test_exports_are_generated():
    questionnaire = demo_questionnaire()
    metadata = QuestionnaireMetadata(
        application_mode="Online autoaplicado",
        primary_device="Computador",
        target_audience="Beneficiários",
        audience_profile="Público heterogéneo",
    )
    findings = run_deterministic_review(questionnaire, metadata)
    synthesis = synthesise(questionnaire, metadata, findings)

    assert export_docx(questionnaire, metadata, findings, synthesis).startswith(b"PK")
    assert export_xlsx(questionnaire, metadata, findings, synthesis).startswith(b"PK")
    assert b'"product": "SURV4IMPACT AI' in export_json(
        questionnaire, metadata, findings, synthesis
    )

