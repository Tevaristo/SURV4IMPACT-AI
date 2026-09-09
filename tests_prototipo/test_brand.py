"""Regressões técnicas do cabeçalho; não executam análise nem chamadas à API."""
from pathlib import Path
import re
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from prototipo.norma import NORMA, ROOT
from prototipo.ui import brand


def assert_native_header(app):
    headers = [b for b in app.get("flex_container") if b.proto.id.endswith("-institutional_header")]
    assert len(headers) == 1
    assert len(app.image) == 3
    assert [c.value for c in headers[0].get("caption")] == [
        'Entidade responsável<br><span style="white-space: nowrap;">IPPS-Iscte</span>',
        "AD&C", "Programa e cofinanciamento"]
    assert headers[0].get("caption")[0].allow_html
    assert len([title for title in app.title if title.value == "SURV4IMPACT AI"]) == 1
    for element in app.image:
        assert len(element.proto.imgs) == 1
        assert element.proto.imgs[0].url.startswith("/mock/media/")
        assert not element.proto.imgs[0].url.startswith("data:")
    # O bloco antigo podia passar testes de presença dos nomes mesmo mostrando
    # HTML literal. Agora nenhum componente textual pode receber essa marcação.
        for kind in ("markdown", "text", "caption", "code"):
            for node in app.get(kind):
                value = str(getattr(node, "value", "")).casefold()
                assert "base64" not in value
                assert "data:image" not in value
                assert "<div" not in value and "<img" not in value and "<style" not in value
        # CSS renderizado por st.html não é conteúdo textual visível. Continua
        # proibido incorporar no HTML imagens, base64 ou o antigo cabeçalho.
        for node in app.get("html"):
            value = str(getattr(node, "value", "")).casefold()
            assert "base64" not in value and "data:image" not in value
            assert "<div" not in value and "<img" not in value
            assert "assets/brand" not in value and "assets\\brand" not in value
            assert str(ROOT).casefold() not in value


def test_native_images_resolve_paths_from_python_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    # Espião sobre st.image: os recursos chegam ao componente de imagem como
    # caminhos absolutos dos ficheiros originais, nunca como texto/base64.
    with patch("prototipo.ui.st.image") as show:
        brand()
    paths = [call.args[0] for call in show.call_args_list]
    assert paths == [ROOT / "assets/brand" / n for n in (
        "ipps-iscte.png", "adc.png", "pat2030-portugal2030-ue.png")]
    assert all(isinstance(p, Path) and p.is_absolute() and p.is_file() for p in paths)
    assert [call.kwargs["width"] for call in show.call_args_list] == [190, 180, 450]
    assert all("height" not in call.kwargs for call in show.call_args_list)


def test_header_from_different_working_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    app = AppTest.from_file(str(ROOT / "app_prototipo.py"), default_timeout=30).run()
    assert not app.exception
    assert_native_header(app)
    # A apresentação deve reproduzir a fonte normativa, sem abreviar nomes.
    source = NORMA.read_text(encoding="utf-8")
    domain = re.search(r"Os três integram \*\*([^*]+)\*\*", source).group(1)
    criteria = re.findall(r"^\*\*(D2\.[346] — [^*]+)\*\*", source, re.MULTILINE)
    scopes = [b for b in app.get("flex_container") if b.proto.id.endswith("-methodological_scope")]
    assert len(scopes) == 1
    captions = scopes[0].get("caption")
    assert captions[0].value.replace("\u00a0", " ") == f"**Domínio {domain}**"
    assert captions[1].value == "**Critérios analisados:**"
    lines = captions[2].value.splitlines()
    assert [line.replace("\u00a0", " ").strip() for line in lines] == criteria
    assert len(lines) == 3 and all("\u00a0—\u00a0" in line for line in lines)
    assert all(not caption.allow_html for caption in captions)
    assert any(m.value == "**Assistente de Revisão Metodológica de Questionários**" for m in app.markdown)
    assert not any("Protótipo documental" in c.value for c in app.caption)


def test_header_uses_native_wrap_and_vertical_alignment():
    app = AppTest.from_file(str(ROOT / "app_prototipo.py"), default_timeout=30).run()
    assert_native_header(app)
    blocks = app.get("flex_container")
    row = next(b.proto.flex_container for b in blocks if b.proto.flex_container.wrap)
    assert row.direction == row.HORIZONTAL
    assert row.align == row.ALIGN_CENTER
    widths = [b.proto.width_config.pixel_width for b in blocks if b.proto.width_config.pixel_width]
    assert widths == [190, 180, 450]
