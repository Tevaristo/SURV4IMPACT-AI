import pytest
from pydantic import ValidationError

from prototipo.engine import payload
from prototipo.models import Element, SELECTION_RULES
from prototipo.reporting import export_json
from prototipo.state import fingerprint, new_session, save_representation


BASE = {"id": "P1", "texto": "Escolha uma resposta.", "localizacao": "p. 1", "formato": "escolha única"}


def element(**limits):
    return Element(**BASE, **limits)


@pytest.mark.parametrize(
    "limits",
    [
        {"regra_selecao": "Número exato de respostas", "numero_minimo": 2, "numero_maximo": 3},
        {"regra_selecao": "Até ao máximo indicado"},
        {"regra_selecao": "Pelo menos o mínimo indicado"},
        {"regra_selecao": "Entre o mínimo e o máximo indicados", "numero_minimo": 4, "numero_maximo": 2},
        {"regra_selecao": "Uma única resposta", "numero_minimo": 1, "numero_maximo": 2},
        {"regra_selecao": "Outra condição indicada no questionário"},
    ],
)
def test_selection_rule_rejects_incoherent_values(limits):
    with pytest.raises(ValidationError):
        element(**limits)


def test_selection_rule_accepts_coherent_values_and_nonnegative_integers():
    value = element(
        regra_selecao="Entre o mínimo e o máximo indicados",
        numero_minimo=1,
        numero_maximo=3,
    )
    assert value.restricoes == "entre 1 e 3 respostas"
    with pytest.raises(ValidationError):
        element(regra_selecao="Pelo menos o mínimo indicado", numero_minimo=-1)


def test_single_response_requires_minimum_and_maximum_equal_to_one():
    value = element(regra_selecao="Uma única resposta", numero_minimo=1, numero_maximo=1)
    assert value.numero_minimo == value.numero_maximo == 1
    assert value.restricoes == "uma resposta"


def test_unconfirmed_selection_rule_is_explicit_and_has_no_derived_numbers():
    value = element(regra_selecao="Não foi possível confirmar")
    assert value.regra_selecao == "Não foi possível confirmar"
    assert value.numero_minimo is None and value.numero_maximo is None
    assert value.restricoes == "não confirmadas"


def test_legacy_text_is_preserved_without_interpretive_conversion():
    raw = "uma resposta por pergunta; valores de 1 a 5"
    value = element(restricoes=raw)
    assert value.regra_selecao == "Outra condição indicada no questionário"
    assert value.outra_condicao_resposta == raw
    assert value.restricoes == raw
    assert Element.model_validate(value.model_dump()).model_dump() == value.model_dump()


def test_canonical_legacy_values_migrate_without_losing_compatibility():
    assert element(restricoes="não confirmadas").regra_selecao == "Não foi possível confirmar"
    assert element(restricoes="nenhuma").regra_selecao == "Sem limite explícito"
    single = element(restricoes="uma resposta")
    assert single.regra_selecao == "Uma única resposta"
    assert single.numero_minimo == single.numero_maximo == 1


def test_structured_limits_participate_in_hash_and_dependency_invalidation():
    session = new_session()
    original = element(regra_selecao="Até ao máximo indicado", numero_maximo=2).model_dump()
    changed = element(regra_selecao="Até ao máximo indicado", numero_maximo=3).model_dump()
    session["representacao"] = [original]
    session["verificacoes"] = {"D2.6-R01": {"dependencias": ["P1"]}}
    assert fingerprint(original) != fingerprint(changed)
    save_representation(session, [changed], False)
    assert "D2.6-R01" not in session["verificacoes"]
    assert session["revisao"] == 1


def test_schema_migration_alone_does_not_invalidate_legacy_session():
    session = new_session()
    legacy = {**BASE, "restricoes": "condição antiga conservada literalmente"}
    session["representacao"] = [legacy]
    session["verificacoes"] = {"D2.6-R01": {"dependencias": ["P1"]}}
    save_representation(session, [Element.model_validate(legacy).model_dump()], False)
    assert "D2.6-R01" in session["verificacoes"]
    assert session["revisao"] == 0


def test_compatibility_text_and_structured_limits_reach_api_and_json_report():
    session = new_session()
    value = element(regra_selecao="Até ao máximo indicado", numero_maximo=3).model_dump()
    session["representacao"] = [value]
    api_element = payload(session)["representacao"][0]
    assert api_element["regra_selecao"] == "Até ao máximo indicado"
    assert api_element["numero_maximo"] == 3
    assert api_element["restricoes"] == "máximo de 3 respostas"
    report = export_json(session).decode("utf-8")
    assert '"regra_selecao": "Até ao máximo indicado"' in report
    assert '"restricoes": "máximo de 3 respostas"' in report


def test_all_requested_selection_rules_are_available():
    assert SELECTION_RULES == [
        "Não aplicável",
        "Não foi possível confirmar",
        "Uma única resposta",
        "Número exato de respostas",
        "Até ao máximo indicado",
        "Pelo menos o mínimo indicado",
        "Entre o mínimo e o máximo indicados",
        "Sem limite explícito",
        "Outra condição indicada no questionário",
    ]
