"""Corpus de QA separado do motor. Secção B → análise; C/D → avaliação posterior."""
from hashlib import sha256
from pathlib import Path
import re
from prototipo.norma import ROOT

SOURCE = ROOT.parent / "base de conhecimento SURV4IMPACT ai REVIEW TOOL/casos_teste/casos_teste_metodologicos_v11.md"
CT12A_SOURCE = SOURCE.parent / "validacao_metodologica_ct12a_v03.md"
APPROVED = ("CT-01A", "CT-01B", "CT-01C", "CT-03", "CT-04A", "CT-08A", "CT-12A", "CT-13")
PROVISIONAL = ("CT-02", "CT-04B", "CT-10A", "CT-10C", "CT-12B")
# Mapeamento direto da tabela de validação V02; referências auxiliares não ampliam o teste.
DIRECT_RULES = {
    "CT-01A": ["D2.3-R05"], "CT-01B": ["D2.3-R05"], "CT-01C": ["D2.3-R05"],
    "CT-02": ["D2.4-R05"], "CT-03": ["D2.4-R06"],
    "CT-04A": ["D2.6-R01", "D2.6-R07"], "CT-04B": ["D2.6-R01", "D2.6-R04", "D2.6-R07"],
    "CT-08A": ["D2.4-R01", "D2.4-R05"], "CT-10A": ["D2.4-R03"], "CT-10C": ["D2.4-R05"],
    "CT-12A": ["D2.6-R08"], "CT-12B": ["D2.6-R08"], "CT-13": ["D2.3-R03"],
}


def cases():
    raw = SOURCE.read_bytes()
    text = raw.decode("utf-8-sig")
    result = {}
    for match in re.finditer(r"^## (CT-[0-9]+[A-Z]?) — (.*?)(?=^## |\Z)", text, re.M | re.S):
        code, body = match.groups()
        if code not in APPROVED + PROVISIONAL:
            continue
        parts = {}
        for m in re.finditer(r"^### ([A-F])\.[^\n]*\n(.*?)(?=^### |\Z)", body, re.M | re.S):
            parts[m.group(1)] = m.group(2).strip()
        result[code] = {"id": code, "estatuto": "Aprovado" if code in APPROVED else "Provisório coerente — não aprovado",
            "input": parts["B"], "expectativas": parts["C"] + "\n\n" + parts["D"],
            "regras": DIRECT_RULES[code],
            "fonte": SOURCE.name, "sha256": sha256(raw).hexdigest()}
    # A decisão posterior da responsável substitui apenas CT-12A. A secção B
    # continua separada das expectativas C/D para nunca as enviar ao modelo.
    revised_raw = CT12A_SOURCE.read_bytes()
    revised = revised_raw.decode("utf-8-sig")
    parts = {m.group(1): m.group(2).strip() for m in re.finditer(
        r"^### ([B-D])\.[^\n]*\n(.*?)(?=^### |\Z)", revised, re.M | re.S
    )}
    if set(parts) != {"B", "C", "D"}:
        raise ValueError("A revisão posterior de CT-12A não separa entrada e expectativas.")
    result["CT-12A"] = {
        "id": "CT-12A",
        "estatuto": "Aprovado",
        "revisao": "Decisão metodológica posterior da responsável — 2026-09-09",
        "input": parts["B"],
        "expectativas": parts["C"] + "\n\n" + parts["D"],
        "regras": DIRECT_RULES["CT-12A"],
        "fonte": CT12A_SOURCE.name,
        "sha256": sha256(revised_raw).hexdigest(),
    }
    if set(result) != set(APPROVED + PROVISIONAL):
        raise ValueError("Faltam casos obrigatórios no corpus V11.")
    return result
