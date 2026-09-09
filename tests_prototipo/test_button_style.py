"""Hierarquia visual dos botões; não executa análises nem chamadas à API."""
from pathlib import Path
import tomllib

from streamlit.testing.v1 import AppTest

from prototipo.norma import ROOT


BRAND_PRIMARY = "#0d28c2"


def app():
    return AppTest.from_file(str(ROOT / "app_prototipo.py"), default_timeout=30).run()


def button_type(application, label):
    return next(button.proto.type for button in application.button if button.label == label)


def contrast(foreground, background):
    def luminance(value):
        channels = [int(value[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        channels = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
                    for channel in channels]
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def test_brand_primary_is_central_and_matches_both_streamlit_themes():
    css = (ROOT / "assets/prototipo_buttons.css").read_text(encoding="utf-8").casefold()
    config = tomllib.loads((ROOT / ".streamlit/config.toml").read_text(encoding="utf-8"))

    assert f"--brand-primary: {BRAND_PRIMARY};" in css
    assert config["theme"]["sidebar"]["primaryColor"].casefold() == BRAND_PRIMARY
    assert '.stbutton > button[kind="primary"]' not in css

    application = app()
    style_blocks = [node for node in application.get("html") if "--brand-primary" in node.proto.body]
    assert len(style_blocks) == 1


def test_download_style_is_scoped_and_defines_all_interaction_states():
    css = (ROOT / "assets/prototipo_buttons.css").read_text(encoding="utf-8").casefold()
    for kind in ("primary", "secondary"):
        selector = f'button[data-testid="stbasebutton-{kind}"]'
        assert selector in css
        for state in (":hover", ":focus-visible", ":active", ":disabled"):
            assert selector + state in css


def test_button_text_contrast_remains_legible_in_defined_states():
    assert contrast("#ffffff", BRAND_PRIMARY) >= 4.5
    assert contrast(BRAND_PRIMARY, "#ffffff") >= 4.5
    assert contrast(BRAND_PRIMARY, "#eef0ff") >= 4.5
    assert contrast("#5f6a74", "#eef1f4") >= 4.5


def test_primary_and_secondary_actions_keep_their_roles_across_the_route():
    application = app()
    assert button_type(application, "Usar questionário de exemplo") == "secondary"
    assert button_type(application, "Extrair / substituir instrumento") == "primary"
    assert button_type(application, "Instrumento e contexto") == "primary"
    assert button_type(application, "Rever a leitura do questionário") == "secondary"
    assert button_type(application, "Nova análise") == "tertiary"

    application.button(key="demo").click().run()
    assert button_type(application, "Guardar opções desta pergunta") == "secondary"
    assert button_type(application, "Substituir a leitura automática") == "tertiary"
    assert button_type(application, "Guardar e confirmar a leitura") == "primary"
    assert button_type(application, "Continuar para apreciação") == "primary"
    downloads = {button.label: button.proto.type for button in application.download_button}
    assert downloads == {
        "Descarregar tabela em Excel": "secondary",
        "Descarregar em CSV": "secondary",
    }

    next(c for c in application.checkbox if c.label.startswith("Revi a leitura apresentada")).check().run()
    next(b for b in application.button if b.label == "Guardar e confirmar a leitura").click().run()
    application.button(key="nav_review").click().run()
    assert button_type(application, "Executar verificações pendentes") == "primary"
    assert button_type(application, "Continuar para esclarecimentos") == "primary"

    application.session_state["prototype"]["pedidos"] = [{
        "id": "pedido-estilo",
        "regra": "D2.4-R01",
        "pergunta": "Pedido técnico para verificar o tipo do botão.",
        "justificacao": "Teste de apresentação.",
        "estado": "pendente",
        "respostas": [],
    }]
    application.button(key="nav_clarifications").click().run()
    assert button_type(application, "Guardar resposta / fecho") == "primary"
    assert button_type(application, "Retomar verificações dependentes") == "primary"
    assert button_type(application, "Continuar para decisão humana") == "secondary"

    application.button(key="nav_decisions").click().run()
    for criterion in ("D2.3", "D2.4", "D2.6"):
        assert button_type(application, "Preparar proposta fundamentada — " + criterion) == "primary"
    assert button_type(application, "Preparar relatório") == "primary"

    application.session_state["prototype"]["propostas"]["D2.4"] = {
        "criterio": "D2.4",
        "estado": "Concluída",
        "categoria": "Cumpre parcialmente",
        "evidencia_adequacao": "Marcador técnico de apresentação.",
        "lacuna_motivo": "Marcador técnico de apresentação.",
        "consequencia": "Não avaliada neste teste.",
        "alcance": "Teste de interface.",
        "atenuantes": "Nenhum.",
        "efeito_conjunto": "Não avaliado neste teste.",
        "justificacao": "Objeto criado apenas para apresentar o formulário.",
        "acao": "Decisão humana necessária.",
        "limites": "Sem resultado metodológico.",
    }
    application.run()
    assert button_type(application, "Guardar decisão — D2.4") == "primary"

    application.button(key="nav_report").click().run()
    report_downloads = {button.label: button.proto.type for button in application.download_button}
    assert report_downloads == {"Descarregar DOCX": "secondary", "Descarregar JSON": "secondary"}


def test_old_confirmation_wording_is_absent_from_tracked_interface_sources():
    visible_sources = [ROOT / "prototipo/ui.py", *Path(ROOT / "tests_prototipo").glob("*.py")]
    text = "\n".join(path.read_text(encoding="utf-8") for path in visible_sources)
    assert "Revi a leitura apresentada" in text
    old_wording = "Revisei" + " a leitura apresentada"
    assert old_wording not in text
