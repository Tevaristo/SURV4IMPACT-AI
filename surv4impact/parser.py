from __future__ import annotations

import io
import re
import statistics
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from pdfminer.pdfexceptions import PDFException
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .models import Question, Questionnaire


QUESTION_NUMBER_RE = re.compile(
    r"^(?:(?:quest[aã]o|pergunta|item|q)\s*)?(\d{1,3}(?:[.\-]\d{1,3})?)[.)\-:]?\s+(.+)$",
    re.IGNORECASE,
)
OPTION_MARKER_PATTERN = (
    r"(?:[☐□■▪◻◼✓✔•●○]|\([ xX]\)|\[[ xX]\]|[a-zA-Z]\)|\d+[.)])"
)
OPTION_RE = re.compile(rf"^(?:{OPTION_MARKER_PATTERN})\s*(.+)$")
INLINE_OPTION_MARKER_RE = re.compile(rf"(?:^|\s)(?:{OPTION_MARKER_PATTERN})\s*")
BARE_NUMERIC_OPTION_RE = re.compile(r"^\d{1,4}(?:[.,]\d+)?(?:\s*[-–]\s*\d{1,4})?$")
ROUTING_RE = re.compile(
    r"\b(?:se respondeu|se assinalou|passe para|avance para|vá para|ir para|siga para|salte para|skip|go to)\b",
    re.IGNORECASE,
)
LIKERT_RE = re.compile(
    r"(?:discordo|concordo|satisfeit|insatisfeit|nada|muito|sempre|nunca|excelente|mau|má|adequad)",
    re.IGNORECASE,
)
PAGE_NUMBER_RE = re.compile(
    r"^(?:p[áa]gina\s*)?\d{1,4}(?:\s*(?:/|de)\s*\d{1,4})?$", re.IGNORECASE
)

MAX_PDF_BYTES = 50 * 1024 * 1024
MAX_PDF_PAGES = 300


class QuestionnaireParseError(ValueError):
    """A safe, user-facing error raised when a questionnaire cannot be read."""


@dataclass(slots=True)
class _TextBlock:
    text: str
    source: str
    min_font_pt: float | None = None
    heading_hint: bool = False


@dataclass(slots=True)
class _TableBlock:
    rows: list[list[str]]
    source: str


_DocumentBlock = _TextBlock | _TableBlock


@dataclass(slots=True)
class _PdfLine:
    text: str
    source: str
    page_number: int
    x0: float
    x1: float
    top: float
    bottom: float
    min_font_pt: float | None
    max_font_pt: float | None
    bold_ratio: float
    boundary: bool
    heading_hint: bool = False


@dataclass(slots=True)
class _PositionedTable:
    block: _TableBlock
    top: float
    bottom: float
    x0: float
    x1: float


@dataclass(slots=True)
class _PdfPage:
    number: int
    height: float
    lines: list[_PdfLine]
    tables: list[_PositionedTable]
    table_detection_failed: bool = False


def _iter_blocks(parent: DocumentObject) -> Iterator[Paragraph | Table]:
    for child in parent.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _normalise_table_rows(rows: Iterable[Iterable[object]]) -> list[list[str]]:
    cleaned: list[list[str]] = []
    for row in rows:
        cells = [_normalise(str(cell or "")) for cell in row]
        while cells and not cells[-1]:
            cells.pop()
        if any(cells):
            cleaned.append(cells)
    return cleaned


def _font_sizes(paragraph: Paragraph) -> list[float]:
    sizes: list[float] = []
    for run in paragraph.runs:
        if run.font.size:
            sizes.append(float(run.font.size.pt))
    return sizes


def _looks_like_text_heading(text: str) -> bool:
    return bool(
        len(text) <= 90
        and not text.endswith(("?", ":"))
        and len(text.split()) <= 10
        and text.upper() == text
        and any(char.isalpha() for char in text)
    )


def _looks_like_heading(paragraph: Paragraph, text: str) -> bool:
    style = (paragraph.style.name if paragraph.style else "").lower()
    if "heading" in style or "título" in style or "titulo" in style:
        return True
    return _looks_like_text_heading(text)


def _question_parts(text: str) -> tuple[str, str] | None:
    match = QUESTION_NUMBER_RE.match(text)
    if match:
        return match.group(1), match.group(2).strip()
    if text.endswith("?"):
        return "", text
    return None


def _marked_options(text: str) -> list[str]:
    """Return one or more options encoded with bullets, boxes, or inline markers."""
    matches = list(INLINE_OPTION_MARKER_RE.finditer(text))
    if not matches or matches[0].start() != 0:
        return []
    options: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        option = text[match.end() : end].strip()
        if option:
            options.append(option)
    return options


def _question_type(text: str, options: list[str], matrix_rows: int = 0) -> str:
    joined = " ".join(options)
    if matrix_rows:
        return "grelha/matriz"
    if not options:
        if re.search(r"\b(quantos?|número|idade|valor|percentagem)\b", text, re.I):
            return "numérica"
        return "aberta"
    if len(options) == 2 and re.search(r"\b(sim|não)\b", joined, re.I):
        return "sim/não"
    if LIKERT_RE.search(joined):
        return "escala"
    if re.search(r"(?:selecione|assinale).*(?:todas|até|mais de uma)", text, re.I):
        return "escolha múltipla"
    return "escolha única"


def _question_label(number: str, index: int) -> str:
    return f"Q{number}" if number else f"Q{index}"


def _build_question(
    questions: list[Question],
    *,
    section: str,
    text: str,
    number: str = "",
    options: list[str] | None = None,
    source: str = "",
    matrix_rows: int = 0,
    matrix_columns: int = 0,
    min_font_pt: float | None = None,
) -> Question:
    question_options = options or []
    index = len(questions) + 1
    question = Question(
        id=f"question-{index}",
        label=_question_label(number, index),
        text=text,
        section=section,
        options=question_options,
        question_type=_question_type(text, question_options, matrix_rows),
        source=source,
        word_count=len(re.findall(r"\b[\wÀ-ÿ'-]+\b", text)),
        matrix_rows=matrix_rows,
        matrix_columns=matrix_columns,
        min_font_pt=min_font_pt,
        routing_text=text if ROUTING_RE.search(text) else "",
        required=bool(re.search(r"(?:\*|obrigat[oó]ri[ao])", text, re.I)),
    )
    questions.append(question)
    return question


def _set_question_shape(question: Question) -> None:
    question.word_count = len(re.findall(r"\b[\wÀ-ÿ'-]+\b", question.text))
    question.question_type = _question_type(
        question.text, question.options, question.matrix_rows
    )
    if not question.routing_text and ROUTING_RE.search(question.text):
        question.routing_text = question.text


def _table_dimensions(rows: list[list[str]]) -> tuple[int, int]:
    return max(0, len(rows) - 1), max((len(row) for row in rows), default=0)


def _unique_nonempty_cells(rows: Iterable[Iterable[str]]) -> list[str]:
    values: list[str] = []
    for row in rows:
        for cell in row:
            if cell and cell not in values:
                values.append(cell)
    return values


def _is_credible_matrix(rows: list[list[str]]) -> bool:
    matrix_rows, matrix_columns = _table_dimensions(rows)
    if matrix_rows < 1 or matrix_columns < 3:
        return False
    response_headers = [cell for cell in rows[0][1:] if cell]
    row_labels = [row[0] for row in rows[1:] if row and row[0]]
    return len(response_headers) >= 2 and bool(row_labels)


def _attach_table_to_question(question: Question, rows: list[list[str]]) -> None:
    matrix_rows, matrix_columns = _table_dimensions(rows)
    if _is_credible_matrix(rows):
        options = [cell for cell in rows[0][1:] if cell]
        question.matrix_rows = max(question.matrix_rows, matrix_rows)
        question.matrix_columns = max(question.matrix_columns, matrix_columns)
    else:
        options = _unique_nonempty_cells(rows)
    for option in options:
        if option not in question.options:
            question.options.append(option)
    _set_question_shape(question)


def _assemble_questionnaire(
    blocks: Iterable[_DocumentBlock],
    *,
    title: str,
    filename: str,
    format_name: str,
    initial_warnings: Iterable[str] = (),
) -> Questionnaire:
    questions: list[Question] = []
    sections: list[str] = []
    instructions: list[str] = []
    raw_parts: list[str] = []
    warnings = list(initial_warnings)
    current_section = "Sem secção"
    current_question: Question | None = None

    for block in blocks:
        if isinstance(block, _TextBlock):
            text = _normalise(block.text)
            if not text:
                continue
            raw_parts.append(text)

            possible_options = _marked_options(text)
            possible_routing = ROUTING_RE.search(text)
            if (block.heading_hint or _looks_like_text_heading(text)) and not (
                current_question and (possible_options or possible_routing)
            ):
                current_section = text
                if text not in sections:
                    sections.append(text)
                current_question = None
                continue

            parts = _question_parts(text)
            numbered_match = QUESTION_NUMBER_RE.match(text)
            numbered_question = bool(
                parts
                and numbered_match
                and (
                    text.endswith(("?", ":"))
                    or len(parts[1].split()) >= 4
                    or current_question is None
                )
            )
            if parts and (numbered_question or (not numbered_match and text.endswith("?"))):
                current_question = _build_question(
                    questions,
                    section=current_section,
                    text=parts[1],
                    number=parts[0],
                    source=block.source,
                    min_font_pt=block.min_font_pt,
                )
                continue

            if possible_options and current_question:
                for option in possible_options:
                    if option not in current_question.options:
                        current_question.options.append(option)
                _set_question_shape(current_question)
                continue

            if current_question and BARE_NUMERIC_OPTION_RE.fullmatch(text):
                if text not in current_question.options:
                    current_question.options.append(text)
                _set_question_shape(current_question)
                continue

            if possible_routing and current_question:
                current_question.routing_text = text
                instructions.append(text)
                continue

            instructions.append(text)
            current_question = None
            continue

        rows = _normalise_table_rows(block.rows)
        if not rows:
            continue
        raw_parts.extend(" | ".join(cell for cell in row if cell) for row in rows)
        first_row = rows[0]
        first_cell = first_row[0] if first_row else ""
        parts = _question_parts(first_cell)
        matrix_rows, matrix_columns = _table_dimensions(rows)

        if parts:
            options = [cell for cell in first_row[1:] if cell]
            if len(rows) > 1 and not options:
                options = [row[0] for row in rows[1:] if row and row[0]]
            is_matrix = _is_credible_matrix(rows)
            current_question = _build_question(
                questions,
                section=current_section,
                text=parts[1],
                number=parts[0],
                options=options,
                source=block.source,
                matrix_rows=matrix_rows if is_matrix else 0,
                matrix_columns=matrix_columns if is_matrix else 0,
            )
        elif first_cell.endswith((":", "?")) and (len(rows) > 1 or matrix_columns > 1):
            is_matrix = _is_credible_matrix(rows)
            options = (
                [cell for cell in first_row[1:] if cell]
                if is_matrix
                else _unique_nonempty_cells([first_row[1:], *rows[1:]])
            )
            current_question = _build_question(
                questions,
                section=current_section,
                text=first_cell,
                options=options,
                source=block.source,
                matrix_rows=matrix_rows if is_matrix else 0,
                matrix_columns=matrix_columns if is_matrix else 0,
            )
        elif current_question is not None:
            # Fixed-layout PDFs often place answers or a matrix immediately
            # after the prompt. Distinguish simple option layouts from matrices.
            _attach_table_to_question(current_question, rows)
        else:
            instructions.append(" | ".join(cell for cell in first_row if cell))
            current_question = None

    if not sections:
        sections = sorted({question.section for question in questions})

    if not questions:
        warnings.append(
            "Não foi possível identificar perguntas automaticamente. "
            f"Verifique se o {format_name} contém texto editável e numeração clara."
        )
    elif len(questions) < 3:
        warnings.append(
            "Foram identificadas poucas perguntas; confirme se existem perguntas "
            "em caixas de texto, imagens ou elementos gráficos."
        )

    return Questionnaire(
        title=title,
        questions=questions,
        sections=sections,
        instructions=instructions,
        raw_text="\n".join(raw_parts),
        source_name=filename,
        parse_warnings=list(dict.fromkeys(warnings)),
    )


def parse_docx(data: bytes, filename: str = "questionario.docx") -> Questionnaire:
    document = Document(io.BytesIO(data))
    title = Path(filename).stem
    if document.core_properties.title:
        title = document.core_properties.title

    blocks: list[_DocumentBlock] = []
    for block_index, block in enumerate(_iter_blocks(document), start=1):
        if isinstance(block, Paragraph):
            text = _normalise(block.text)
            if not text:
                continue
            sizes = _font_sizes(block)
            blocks.append(
                _TextBlock(
                    text=text,
                    source=f"Parágrafo {block_index}",
                    min_font_pt=min(sizes) if sizes else None,
                    heading_hint=_looks_like_heading(block, text),
                )
            )
        else:
            rows = _normalise_table_rows(
                [[cell.text for cell in row.cells] for row in block.rows]
            )
            if rows:
                blocks.append(_TableBlock(rows=rows, source=f"Tabela {block_index}"))

    return _assemble_questionnaire(
        blocks,
        title=title,
        filename=filename,
        format_name="DOCX",
    )


def _line_in_table(line: _PdfLine, table: _PositionedTable) -> bool:
    centre_x = (line.x0 + line.x1) / 2
    centre_y = (line.top + line.bottom) / 2
    return (
        table.x0 - 1 <= centre_x <= table.x1 + 1
        and table.top - 1 <= centre_y <= table.bottom + 1
    )


def _pdf_line_from_mapping(
    line: dict[str, object], *, page_number: int, line_number: int, page_height: float
) -> _PdfLine | None:
    text = _normalise(str(line.get("text") or ""))
    if not text:
        return None

    chars = list(line.get("chars") or [])
    sizes = [
        float(char["size"])
        for char in chars
        if isinstance(char, dict) and isinstance(char.get("size"), (int, float))
    ]
    font_names = [
        str(char.get("fontname") or "").casefold()
        for char in chars
        if isinstance(char, dict)
    ]
    bold_count = sum(
        any(marker in font for marker in ("bold", "black", "semibold", "demi"))
        for font in font_names
    )
    top = float(line.get("top") or 0)
    bottom = float(line.get("bottom") or top)
    return _PdfLine(
        text=text,
        source=f"Página {page_number}, linha {line_number}",
        page_number=page_number,
        x0=float(line.get("x0") or 0),
        x1=float(line.get("x1") or 0),
        top=top,
        bottom=bottom,
        min_font_pt=min(sizes) if sizes else None,
        max_font_pt=max(sizes) if sizes else None,
        bold_ratio=(bold_count / len(font_names)) if font_names else 0.0,
        boundary=top <= page_height * 0.07 or bottom >= page_height * 0.93,
    )


def _extract_pdf_page(page: object, page_number: int) -> _PdfPage:
    deduped = page.dedupe_chars()
    page_height = float(deduped.height)
    tables: list[_PositionedTable] = []
    table_detection_failed = False
    try:
        found_tables = deduped.find_tables()
    except (PDFException, ValueError, TypeError, KeyError, IndexError):
        found_tables = []
        table_detection_failed = True

    for table_number, table in enumerate(found_tables, start=1):
        try:
            rows = _normalise_table_rows(table.extract())
        except (PDFException, ValueError, TypeError, KeyError, IndexError):
            table_detection_failed = True
            continue
        if not rows:
            continue
        x0, top, x1, bottom = (float(value) for value in table.bbox)
        tables.append(
            _PositionedTable(
                block=_TableBlock(
                    rows=rows, source=f"Página {page_number}, tabela {table_number}"
                ),
                top=top,
                bottom=bottom,
                x0=x0,
                x1=x1,
            )
        )

    raw_lines = deduped.extract_text_lines(
        strip=True,
        return_chars=True,
        x_tolerance=3,
        y_tolerance=3,
    )
    lines: list[_PdfLine] = []
    for line_number, raw_line in enumerate(raw_lines, start=1):
        line = _pdf_line_from_mapping(
            raw_line,
            page_number=page_number,
            line_number=line_number,
            page_height=page_height,
        )
        if line is not None and not any(_line_in_table(line, table) for table in tables):
            lines.append(line)

    return _PdfPage(
        number=page_number,
        height=page_height,
        lines=lines,
        tables=tables,
        table_detection_failed=table_detection_failed,
    )


def _pdf_heading_hint(line: _PdfLine, body_font_pt: float) -> bool:
    if _looks_like_text_heading(line.text):
        return True
    if line.text.endswith(("?", ":")) or len(line.text.split()) > 12:
        return False
    if not line.max_font_pt or not body_font_pt:
        return False
    relative_size = line.max_font_pt / body_font_pt
    return relative_size >= 1.3 or (
        relative_size >= 1.15 and line.bold_ratio >= 0.5
    )


def _starts_structural_block(line: _PdfLine) -> bool:
    return bool(
        line.heading_hint
        or QUESTION_NUMBER_RE.match(line.text)
        or OPTION_RE.match(line.text)
        or ROUTING_RE.search(line.text)
        or PAGE_NUMBER_RE.fullmatch(line.text)
    )


def _can_merge_pdf_lines(current: _PdfLine, following: _PdfLine, body_font_pt: float) -> bool:
    if current.page_number != following.page_number or _starts_structural_block(following):
        return False
    if current.heading_hint or current.text.endswith(("?", ":")):
        return False
    if current.text.endswith((";", ".")) and not QUESTION_NUMBER_RE.match(current.text):
        return False
    line_gap = following.top - current.bottom
    if line_gap > max(5.0, body_font_pt * 0.9):
        return False
    return abs(following.x0 - current.x0) <= max(28.0, body_font_pt * 3.0)


def _merge_pdf_lines(lines: list[_PdfLine], body_font_pt: float) -> list[_TextBlock]:
    if not lines:
        return []
    merged: list[_TextBlock] = []
    current = lines[0]
    for following in lines[1:]:
        if _can_merge_pdf_lines(current, following, body_font_pt):
            current.text = _normalise(f"{current.text} {following.text}")
            current.x1 = max(current.x1, following.x1)
            current.bottom = following.bottom
            if following.min_font_pt is not None:
                current.min_font_pt = (
                    min(current.min_font_pt, following.min_font_pt)
                    if current.min_font_pt is not None
                    else following.min_font_pt
                )
            continue
        merged.append(
            _TextBlock(
                text=current.text,
                source=current.source,
                min_font_pt=current.min_font_pt,
                heading_hint=current.heading_hint,
            )
        )
        current = following
    merged.append(
        _TextBlock(
            text=current.text,
            source=current.source,
            min_font_pt=current.min_font_pt,
            heading_hint=current.heading_hint,
        )
    )
    return merged


def _boundary_key(line: _PdfLine, page_height: float) -> tuple[str, str, int]:
    band = "top" if line.top <= page_height * 0.07 else "bottom"
    centre = (line.top + line.bottom) / 2
    position_bucket = round((centre / page_height) * 100)
    return line.text.casefold(), band, position_bucket


def _is_structural_pdf_line(line: _PdfLine) -> bool:
    return bool(
        QUESTION_NUMBER_RE.match(line.text)
        or OPTION_RE.match(line.text)
        or ROUTING_RE.search(line.text)
    )


def _repeated_pdf_boundaries(pages: list[_PdfPage]) -> set[tuple[str, str, int]]:
    occurrences: dict[tuple[str, str, int], set[int]] = defaultdict(set)
    for page in pages:
        for line in page.lines:
            if line.boundary and len(line.text) > 1 and not _is_structural_pdf_line(line):
                occurrences[_boundary_key(line, page.height)].add(page.number)
    return {key for key, page_numbers in occurrences.items() if len(page_numbers) >= 2}


def _pdf_blocks(pages: list[_PdfPage]) -> tuple[list[_DocumentBlock], list[int], bool]:
    font_sizes = [
        line.max_font_pt
        for page in pages
        for line in page.lines
        if line.max_font_pt is not None
    ]
    body_font_pt = statistics.median(font_sizes) if font_sizes else 10.0
    repeated_boundaries = _repeated_pdf_boundaries(pages)
    seen_repeated_boundaries: set[tuple[str, str, int]] = set()
    blocks: list[_DocumentBlock] = []
    pages_without_text: list[int] = []
    has_tables = False

    for page in pages:
        visible_lines: list[_PdfLine] = []
        for line in page.lines:
            if line.boundary and PAGE_NUMBER_RE.fullmatch(line.text):
                continue
            boundary_key = _boundary_key(line, page.height)
            if line.boundary and boundary_key in repeated_boundaries:
                if boundary_key in seen_repeated_boundaries:
                    continue
                seen_repeated_boundaries.add(boundary_key)
            visible_lines.append(line)
        for line in visible_lines:
            line.heading_hint = _pdf_heading_hint(line, body_font_pt)

        entries: list[tuple[float, str, _PdfLine | _PositionedTable]] = [
            (line.top, "line", line) for line in visible_lines
        ]
        entries.extend((table.top, "table", table) for table in page.tables)
        entries.sort(key=lambda item: (item[0], 0 if item[1] == "line" else 1))

        pending_lines: list[_PdfLine] = []
        page_has_text = False
        for _, kind, entry in entries:
            if kind == "line":
                assert isinstance(entry, _PdfLine)
                pending_lines.append(entry)
                page_has_text = True
                continue
            if pending_lines:
                blocks.extend(_merge_pdf_lines(pending_lines, body_font_pt))
                pending_lines = []
            assert isinstance(entry, _PositionedTable)
            blocks.append(entry.block)
            page_has_text = page_has_text or any(any(row) for row in entry.block.rows)
            has_tables = True
        if pending_lines:
            blocks.extend(_merge_pdf_lines(pending_lines, body_font_pt))
        if not page_has_text:
            pages_without_text.append(page.number)

    return blocks, pages_without_text, has_tables


def _format_page_numbers(page_numbers: list[int]) -> str:
    return ", ".join(str(number) for number in page_numbers)


def _has_suspicious_glyph_mapping(text: str) -> bool:
    visible = [character for character in text if not character.isspace()]
    if not visible:
        return False
    suspicious = sum(
        character == "�" or "\ue000" <= character <= "\uf8ff" for character in visible
    )
    return suspicious / len(visible) >= 0.01


def _validated_pdf_reader(data: bytes) -> tuple[PdfReader, str]:
    if len(data) > MAX_PDF_BYTES:
        raise QuestionnaireParseError(
            "O PDF excede o limite de 50 MB. Reduza o tamanho do ficheiro e tente novamente."
        )
    if b"%PDF-" not in data[:1024]:
        raise QuestionnaireParseError(
            "O ficheiro não tem uma estrutura PDF válida ou está corrompido."
        )
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            try:
                unlocked = reader.decrypt("")
            except Exception as exc:
                raise QuestionnaireParseError(
                    "O PDF está protegido por palavra-passe. Remova a proteção e tente novamente."
                ) from exc
            if not unlocked:
                raise QuestionnaireParseError(
                    "O PDF está protegido por palavra-passe. Remova a proteção e tente novamente."
                )
        page_count = len(reader.pages)
        if page_count == 0:
            raise QuestionnaireParseError("O PDF não contém páginas.")
        if page_count > MAX_PDF_PAGES:
            raise QuestionnaireParseError(
                f"O PDF tem mais de {MAX_PDF_PAGES} páginas. Divida-o em ficheiros menores."
            )
        metadata_title = ""
        try:
            if reader.metadata and reader.metadata.title:
                metadata_title = _normalise(str(reader.metadata.title))
        except (PdfReadError, ValueError, TypeError):
            metadata_title = ""
        return reader, metadata_title
    except QuestionnaireParseError:
        raise
    except (PdfReadError, ValueError, TypeError, OSError, EOFError) as exc:
        raise QuestionnaireParseError(
            "O ficheiro PDF está corrompido ou incompleto e não pode ser lido."
        ) from exc


def parse_pdf(data: bytes, filename: str = "questionario.pdf") -> Questionnaire:
    _, metadata_title = _validated_pdf_reader(data)
    title = metadata_title or Path(filename).stem
    warnings: list[str] = []
    pages: list[_PdfPage] = []

    try:
        with pdfplumber.open(io.BytesIO(data), unicode_norm="NFC") as document:
            for page_number, page in enumerate(document.pages, start=1):
                try:
                    pages.append(_extract_pdf_page(page, page_number))
                except (PDFException, ValueError, TypeError, KeyError, IndexError):
                    pages.append(
                        _PdfPage(
                            number=page_number,
                            height=float(getattr(page, "height", 1) or 1),
                            lines=[],
                            tables=[],
                        )
                    )
                    warnings.append(
                        f"Não foi possível extrair o conteúdo da página {page_number}."
                    )
                finally:
                    page.close()
    except QuestionnaireParseError:
        raise
    except PDFException as exc:
        message = str(exc).casefold()
        if "password" in message:
            raise QuestionnaireParseError(
                "O PDF está protegido por palavra-passe. Remova a proteção e tente novamente."
            ) from exc
        raise QuestionnaireParseError(
            "O ficheiro PDF está corrompido ou usa uma estrutura que não pode ser lida."
        ) from exc
    except (ValueError, TypeError, OSError, EOFError) as exc:
        raise QuestionnaireParseError(
            "O ficheiro PDF está corrompido ou usa uma estrutura que não pode ser lida."
        ) from exc

    blocks, pages_without_text, has_tables = _pdf_blocks(pages)
    if not blocks:
        raise QuestionnaireParseError(
            "O PDF não contém texto selecionável. Parece ser um documento digitalizado; "
            "aplique OCR e carregue novamente o ficheiro."
        )
    if pages_without_text:
        if len(pages_without_text) == 1:
            warnings.append(
                "Não foi encontrado texto selecionável na página "
                f"{pages_without_text[0]}; confirme se contém uma imagem ou digitalização."
            )
        else:
            warnings.append(
                "Não foi encontrado texto selecionável nas páginas "
                f"{_format_page_numbers(pages_without_text)}; confirme se contêm imagens ou digitalizações."
            )
    if any(page.table_detection_failed for page in pages):
        warnings.append(
            "Não foi possível verificar todas as tabelas do PDF; confirme manualmente as grelhas e opções."
        )
    elif has_tables:
        warnings.append(
            "Foram reconstruídas tabelas do PDF; confirme a associação entre linhas, colunas e opções."
        )

    questionnaire = _assemble_questionnaire(
        blocks,
        title=title,
        filename=filename,
        format_name="PDF",
        initial_warnings=warnings,
    )
    if not questionnaire.questions:
        raise QuestionnaireParseError(
            "Foi encontrado texto no PDF, mas não foi possível identificar perguntas. "
            "Confirme a ordem de leitura e use numeração ou pontos de interrogação claros."
        )
    if _has_suspicious_glyph_mapping(questionnaire.raw_text):
        questionnaire.parse_warnings.append(
            "Alguns caracteres do PDF podem ter sido mapeados incorretamente pela fonte incorporada."
        )
    return questionnaire


def parse_questionnaire(data: bytes, filename: str) -> Questionnaire:
    if not data:
        raise QuestionnaireParseError("O ficheiro está vazio.")

    suffix = Path(filename).suffix.casefold()
    if suffix == ".pdf":
        return parse_pdf(data, filename)
    if suffix == ".docx":
        try:
            return parse_docx(data, filename)
        except Exception as exc:
            raise QuestionnaireParseError(
                "O ficheiro DOCX está corrompido ou não pode ser lido."
            ) from exc
    raise QuestionnaireParseError(
        "Formato não suportado. Carregue um ficheiro DOCX ou PDF."
    )


def reclassify_questions(questionnaire: Questionnaire) -> Questionnaire:
    for question in questionnaire.questions:
        _set_question_shape(question)
    return questionnaire
