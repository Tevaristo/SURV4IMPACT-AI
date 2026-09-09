"""Reutiliza o leitor antigo; inferências nunca são confirmações."""
from io import BytesIO
from hashlib import sha256
from docx import Document
from docx.table import Table
from pypdf import PdfReader
from surv4impact.parser import parse_questionnaire, _iter_blocks
from .models import Element


def extract(data, name):
    if len(data) > 50 * 1024 * 1024:
        raise ValueError("Limite técnico: 50 MB. Use um recorte pertinente ou representação textual.")
    parsed = parse_questionnaire(data, name)
    raw = []
    if name.lower().endswith(".pdf"):
        reader = PdfReader(BytesIO(data))
        for i, page in enumerate(reader.pages, 1):
            raw.append({"localizacao": f"PDF p. {i}", "texto": page.extract_text() or "[Página sem texto extraível]"})
    else:
        for i, block in enumerate(_iter_blocks(Document(BytesIO(data))), 1):
            text = "\n".join(" | ".join(c.text for c in row.cells) for row in block.rows) if isinstance(block, Table) else block.text
            raw.append({"localizacao": f"DOCX bloco {i}", "texto": text})
    elements = [Element(id=q.id, texto=q.text, localizacao=q.source or f"candidato {i}",
        opcoes=q.options, formato="não confirmado", condicoes_destinos=q.routing_text).model_dump()
        for i, q in enumerate(parsed.questions, 1)]
    # Blocos brutos mantêm ordem, grelhas, instruções e texto perdido pela heurística.
    if not elements:
        elements = [Element(id="TEXTO", texto="\n".join(r["localizacao"] + "\n" + r["texto"] for r in raw), localizacao=name).model_dump()]
    return {"nome": name, "titulo_extraido": parsed.title, "sha256": sha256(data).hexdigest(), "texto_bruto": raw,
            "texto_parser": parsed.raw_text, "instrucoes_candidatas": parsed.instructions,
            "avisos": parsed.parse_warnings}, elements


def from_text(text, name="Representação textual fornecida"):
    if not text.strip():
        raise ValueError("Introduza texto do instrumento.")
    return {"nome": name, "sha256": sha256(text.encode()).hexdigest(),
            "texto_bruto": [{"localizacao": "texto fornecido", "texto": text}], "avisos": []}, [
                Element(id="TEXTO", texto=text, localizacao="texto fornecido").model_dump()]
