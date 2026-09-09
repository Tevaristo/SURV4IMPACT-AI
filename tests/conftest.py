from __future__ import annotations

from collections.abc import Sequence

import pytest


def _pdf_string(value: str) -> bytes:
    return (
        value.encode("cp1252")
        .replace(b"\\", b"\\\\")
        .replace(b"(", b"\\(")
        .replace(b")", b"\\)")
    )


def _text_line(x: int, y: int, value: str, *, size: int = 12) -> bytes:
    return (
        f"BT /F1 {size} Tf {x} {y} Td (".encode("ascii")
        + _pdf_string(value)
        + b") Tj ET\n"
    )


def _build_pdf(page_streams: Sequence[bytes], *, title: str) -> bytes:
    """Build a small text PDF without depending on a PDF authoring library."""
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: (
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
            b"/Encoding /WinAnsiEncoding >>"
        ),
    }
    page_ids: list[int] = []
    for index, stream in enumerate(page_streams):
        page_id = 4 + index * 2
        content_id = page_id + 1
        page_ids.append(page_id)
        objects[page_id] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 3 0 R >> >> "
            + f"/Contents {content_id} 0 R >>".encode("ascii")
        )
        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"endstream"
        )

    kids = b" ".join(f"{page_id} 0 R".encode("ascii") for page_id in page_ids)
    objects[2] = (
        b"<< /Type /Pages /Kids [" + kids + f"] /Count {len(page_ids)} >>".encode("ascii")
    )
    info_id = max(objects) + 1
    objects[info_id] = b"<< /Title (" + _pdf_string(title) + b") >>"

    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (info_id + 1)
    for object_id in range(1, info_id + 1):
        offsets[object_id] = len(document)
        document.extend(f"{object_id} 0 obj\n".encode("ascii"))
        document.extend(objects[object_id])
        document.extend(b"\nendobj\n")

    xref_offset = len(document)
    document.extend(f"xref\n0 {info_id + 1}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for object_id in range(1, info_id + 1):
        document.extend(f"{offsets[object_id]:010d} 00000 n \n".encode("ascii"))
    document.extend(
        (
            f"trailer\n<< /Size {info_id + 1} /Root 1 0 R /Info {info_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(document)


def _questionnaire_page() -> bytes:
    return b"".join(
        [
            _text_line(72, 750, "EXPERIÊNCIA", size=16),
            _text_line(72, 710, "1. Nos últimos 12 meses, utilizou o serviço?"),
            _text_line(90, 690, "a) Sim"),
            _text_line(90, 670, "b) Não"),
            _text_line(72, 630, "2. Como avalia o apoio recebido?"),
        ]
    )


def _matrix_page() -> bytes:
    table_lines = b"".join(
        [
            b"0.75 w\n",
            b"72 720 m 500 720 l S\n",
            b"72 680 m 500 680 l S\n",
            b"72 640 m 500 640 l S\n",
            b"72 640 m 72 720 l S\n",
            b"300 640 m 300 720 l S\n",
            b"400 640 m 400 720 l S\n",
            b"500 640 m 500 720 l S\n",
        ]
    )
    return b"".join(
        [
            _text_line(72, 760, "GRELHA DE AVALIAÇÃO", size=16),
            table_lines,
            _text_line(78, 695, "3. Avalie as dimensões seguintes:", size=10),
            _text_line(320, 695, "Baixo", size=10),
            _text_line(420, 695, "Elevado", size=10),
            _text_line(78, 655, "Clareza", size=10),
        ]
    )


def _repeated_options_page(number: int, prompt: str) -> bytes:
    return b"".join(
        [
            _text_line(72, 760, f"{number}. {prompt}?"),
            _text_line(90, 740, "a) Sim"),
            _text_line(90, 720, "b) Não"),
        ]
    )


@pytest.fixture
def questionnaire_pdf_bytes() -> bytes:
    return _build_pdf(
        [_questionnaire_page(), _matrix_page()],
        title="Questionário PDF de teste",
    )


@pytest.fixture
def mixed_blank_pdf_bytes() -> bytes:
    return _build_pdf(
        [b"", _questionnaire_page()],
        title="Questionário com página vazia",
    )


@pytest.fixture
def empty_pdf_bytes() -> bytes:
    return _build_pdf([b""], title="Questionário digitalizado")


@pytest.fixture
def alternate_questionnaire_pdf_bytes() -> bytes:
    return _build_pdf(
        [_questionnaire_page(), _matrix_page()],
        title="Segundo questionário PDF",
    )


@pytest.fixture
def repeated_options_pdf_bytes() -> bytes:
    return _build_pdf(
        [
            _repeated_options_page(1, "Utilizou o serviço"),
            _repeated_options_page(2, "Conhecia o programa"),
        ],
        title="Opções repetidas",
    )


@pytest.fixture
def wrapped_question_pdf_bytes() -> bytes:
    page = b"".join(
        [
            _text_line(72, 700, "1. Recorde a sua participação no programa."),
            _text_line(72, 684, "Que motivo melhor explica a sua escolha?"),
        ]
    )
    return _build_pdf([page], title="Pergunta repartida")


@pytest.fixture
def mid_page_year_pdf_bytes() -> bytes:
    page = b"".join(
        [
            _text_line(72, 700, "1. Em que ano participou?"),
            _text_line(72, 500, "2024"),
        ]
    )
    return _build_pdf([page], title="Ano no conteúdo")


@pytest.fixture
def text_only_pdf_bytes() -> bytes:
    page = b"".join(
        [
            _text_line(72, 740, "NOTA INFORMATIVA", size=16),
            _text_line(72, 700, "Este documento descreve o âmbito do estudo."),
            _text_line(72, 680, "Não contém perguntas destinadas aos participantes."),
        ]
    )
    return _build_pdf([page], title="Documento sem perguntas")
