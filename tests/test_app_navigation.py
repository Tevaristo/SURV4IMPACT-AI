from streamlit.testing.v1 import AppTest


def _button(app: AppTest, label: str):
    matches = [button for button in app.button if button.label == label]
    assert len(matches) == 1
    return matches[0]


def test_brand_system_is_rendered_on_entry():
    app = AppTest.from_file("app.py", default_timeout=30).run()

    assert not list(app.exception)
    brand_markup = next(
        item.value for item in app.markdown if 'class="surv-brand-system"' in item.value
    )
    assert "IPPS-Iscte" in brand_markup
    assert "AD&amp;C" in brand_markup
    assert "PAT 2030, Portugal 2030" in brand_markup
    assert "Cofinanciado pela União Europeia" in brand_markup


def test_questionnaire_uploader_accepts_docx_and_pdf():
    app = AppTest.from_file("app.py", default_timeout=30).run()

    assert not list(app.exception)
    allowed_types = {value.lstrip(".") for value in app.file_uploader[0].allowed_type}
    assert allowed_types == {"docx", "pdf"}


def test_user_can_upload_and_analyse_a_pdf(questionnaire_pdf_bytes: bytes):
    app = AppTest.from_file("app.py", default_timeout=30).run()

    app.file_uploader[0].set_value(
        ("questionario.pdf", questionnaire_pdf_bytes, "application/pdf")
    )
    app.run()
    _button(app, "Analisar questionário").click().run()

    assert not list(app.exception)
    assert app.session_state["stage"] == "Questionário"
    assert app.session_state["uploaded_file_name"] == "questionario.pdf"
    assert app.session_state["uploaded_file_bytes"] == questionnaire_pdf_bytes
    assert app.session_state["questionnaire"].source_name == "questionario.pdf"
    assert app.session_state["questionnaire"].title == "Questionário PDF de teste"
    assert app.session_state["metadata"].title == "Questionário PDF de teste"
    assert len(app.session_state["questionnaire"].questions) == 3


def test_corrupt_pdf_error_does_not_suggest_ocr():
    app = AppTest.from_file("app.py", default_timeout=30).run()

    app.file_uploader[0].set_value(
        ("corrompido.pdf", b"%PDF-1.4\nficheiro truncado", "application/pdf")
    )
    app.run()
    _button(app, "Analisar questionário").click().run()

    assert not list(app.exception)
    assert app.session_state["stage"] == "Carregar"
    assert any("corrompido" in message.value.casefold() for message in app.error)
    assert not any("ocr" in message.value.casefold() for message in app.info)


def test_replacing_a_pdf_uses_the_new_extracted_title(
    questionnaire_pdf_bytes: bytes,
    alternate_questionnaire_pdf_bytes: bytes,
):
    app = AppTest.from_file("app.py", default_timeout=30).run()
    app.file_uploader[0].set_value(
        ("primeiro.pdf", questionnaire_pdf_bytes, "application/pdf")
    )
    app.run()
    _button(app, "Analisar questionário").click().run()

    _button(app, "← Voltar a Carregar").click().run()
    _button(app, "Substituir ficheiro").click().run()
    app.file_uploader[0].set_value(
        ("segundo.pdf", alternate_questionnaire_pdf_bytes, "application/pdf")
    )
    app.run()
    _button(app, "Analisar ficheiro substituto").click().run()

    assert not list(app.exception)
    assert app.session_state["questionnaire"].title == "Segundo questionário PDF"
    assert app.session_state["metadata"].title == "Segundo questionário PDF"


def test_new_analysis_does_not_reuse_the_previous_pdf_title(
    questionnaire_pdf_bytes: bytes,
    alternate_questionnaire_pdf_bytes: bytes,
):
    app = AppTest.from_file("app.py", default_timeout=30).run()
    app.file_uploader[0].set_value(
        ("primeiro.pdf", questionnaire_pdf_bytes, "application/pdf")
    )
    app.run()
    _button(app, "Analisar questionário").click().run()

    _button(app, "Nova análise").click().run()
    app.file_uploader[0].set_value(
        ("segundo.pdf", alternate_questionnaire_pdf_bytes, "application/pdf")
    )
    app.run()
    _button(app, "Analisar questionário").click().run()

    assert not list(app.exception)
    assert app.session_state["questionnaire"].title == "Segundo questionário PDF"
    assert app.session_state["metadata"].title == "Segundo questionário PDF"


def test_user_can_go_back_and_reanalyse_without_uploading_again():
    app = AppTest.from_file("app.py", default_timeout=30).run()

    _button(app, "Usar exemplo demonstrativo").click().run()
    assert app.session_state["stage"] == "Questionário"

    _button(app, "← Voltar a Carregar").click().run()
    assert app.session_state["stage"] == "Carregar"
    assert not list(app.exception)
    assert _button(app, "Substituir ficheiro")
    assert any("Ficheiro mantido na sessão" in message.value for message in app.success)

    _button(app, "Reanalisar questionário atual").click().run()
    assert app.session_state["stage"] == "Questionário"
    assert not list(app.exception)
