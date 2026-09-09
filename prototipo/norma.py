from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
NORMA = ROOT.parent / "base de conhecimento SURV4IMPACT ai REVIEW TOOL" / "criterios_v08.md"
CRITERIOS = ("D2.3", "D2.4", "D2.6")


@lru_cache(maxsize=4)
def _read(path, stamp):
    data = Path(path).read_bytes()
    text = data.decode("utf-8-sig")
    common = text[text.index("### Escala e regras comuns"):text.index("### Correspondência delimitadora")]
    fichas = {}
    rules = {}
    for c in CRITERIOS:
        section = re.search(r"^## Ficha " + re.escape(c) + r"\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S).group(1)
        # Definição, aplicação e decisões atuais; exclui exemplos históricos.
        selected = section[:section.index("### 11.")]
        fichas[c] = selected
        for match in re.finditer(r"^#### (D2\.[346]-R\d+) — (.*?)(?=^#### |^### |\Z)", selected, re.M | re.S):
            rules[match.group(1)] = match.group(0).strip()
    if len(rules) != 24 or any("DM-0" + str(i) not in common for i in range(1, 6)):
        raise ValueError("A estrutura da norma não corresponde à V08 esperada.")
    return {"nome": Path(path).name, "versao": "v08", "sha256": sha256(data).hexdigest(),
            "comum": common, "fichas": fichas, "regras": rules}


def load_norma(path=NORMA):
    path = Path(path)
    return _read(str(path), path.stat().st_mtime_ns)


def provenance():
    n = load_norma()
    return {k: n[k] for k in ("nome", "versao", "sha256")}
