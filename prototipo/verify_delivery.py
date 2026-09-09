"""Evidências locais sem chave ou conteúdo confidencial. Não fabrica análises."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
from .norma import ROOT, provenance
from .state import new_session, save_representation, transition, STAGES
from .demo import load_demo
from .reporting import export_docx, export_json
from .api import configuration, smoke_test


def run():
    folder = ROOT / "evidencias_prototipo"
    baseline = json.loads((folder / "integridade_inicial.json").read_text(encoding="utf-8"))
    changes = []
    for name, digest in baseline.items():
        path = ROOT.parent / name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            changes.append(name)
    data = {"ficheiros_conferidos": len(baseline), "alteracoes": changes,
            "alteracao_autorizada": "surv4impact survey ai review tool/.gitignore",
            "git": "Não disponível no PATH nem nos caminhos usuais verificados; sem commit inicial; cópia externa declarada pelo utilizador.", "norma": provenance()}
    (folder / "preservacao_final.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # Demonstração ilustrativa localizada; API não é substituída. Na ausência de chave,
    # o resultado demonstrado é o percurso local de relatório parcial.
    s = new_session(); load_demo(s)
    save_representation(s, s["representacao"], True)
    stages = []
    for stage in STAGES:
        transition(s, stage); stages.append(stage)
    s["api"] = json.loads((folder / "api_inicial.json").read_text(encoding="utf-8"))
    out = ROOT / "outputs/prototipo_demo"
    out.mkdir(parents=True, exist_ok=True)
    (out / "relatorio_parcial_demo.json").write_bytes(export_json(s))
    (out / "relatorio_parcial_demo.docx").write_bytes(export_docx(s))
    from tests_prototipo.cases import cases
    key, model = configuration()
    corpus = [{"caso": code, "estatuto": case["estatuto"], "fonte": case["fonte"], "sha256": case["sha256"],
        "entrada_e_expectativas_carregadas": True, "execucao_semantica_real": "Não executada — falta de API configurada" if not key else "Consultar resultados pytest live", "aprovacao_da_resposta": "Não atribuída"} for code, case in cases().items()]
    (folder / "casos_metodologicos.json").write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {"percurso_exercitado": stages, "representacao_confirmada": True,
        "instrumento": s["instrumento"]["designacao"],
        "ambito": s["ambito"], "classificacao_integral_validada": False,
        "analise_real_API": False, "decisao_humana_real": False, "relatorio": "Parcial",
        "limite": "Percurso local verificado. Demonstração assistida completa e qualificação semântica pendentes de credenciais. Fixtures técnicas não substituem análise real.",
        "dependencias": {p: importlib.metadata.version(p) for p in ("streamlit", "python-docx", "pdfplumber", "pypdf", "pydantic", "openai", "pandas", "pytest")}}
    (folder / "demonstracao_local.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"preservacao": data, "demonstracao": result}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    run()
