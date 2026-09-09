import sys
from pathlib import Path
import pytest
import importlib.util

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from .fixture_oficina import load_demo
from prototipo.state import new_session, save_representation


@pytest.fixture
def session():
    s = new_session()
    load_demo(s)
    save_representation(s, s["representacao"], True)
    return s


@pytest.fixture
def prototype_pdfs():
    path = Path(__file__).resolve().parents[1] / "tests/conftest.py"
    spec = importlib.util.spec_from_file_location("legacy_pdf_fixtures", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.questionnaire_pdf_bytes.__wrapped__(), module.alternate_questionnaire_pdf_bytes.__wrapped__()
