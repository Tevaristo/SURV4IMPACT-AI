"""Entrada ilustrativa interna; expectativas de QA separadas do payload de análise."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .extraction import from_text
from .models import Element
from .state import replace_document, save_context, transition

RESOURCES = Path(__file__).resolve().parent / "resources"
BASE_RESOURCE = RESOURCES / "exemplo_casos_aprovados_v01.json"
RESOURCE = RESOURCES / "exemplo_casos_aprovados_v02.json"
BASE_METADATA = RESOURCES / "exemplo_casos_aprovados_v01.metadata.json"
METADATA = RESOURCES / "exemplo_casos_aprovados_v02.metadata.json"
EXAMPLE_ID = "casos_aprovados_ilustrativo_v01"
EXAMPLE_TITLE = "Questionário ilustrativo construído a partir de casos metodológicos validados"
EXAMPLE_DESCRIPTION = "Carrega um questionário ilustrativo preparado a partir de casos metodológicos validados, para experimentar o percurso da aplicação."
EXAMPLE_LIMIT = "Os comportamentos associados às situações assinaladas foram validados; a classificação integral do questionário não constitui um resultado histórico validado."


def load_example():
    """Aplica a revisão interna sobre a base preservada, sem consultar fontes externas."""
    example = json.loads(BASE_RESOURCE.read_text(encoding="utf-8"))
    revision = json.loads(RESOURCE.read_text(encoding="utf-8"))
    if hashlib.sha256(BASE_RESOURCE.read_bytes()).hexdigest() != revision["base"]["sha256"]:
        raise RuntimeError("A base preservada do questionário de exemplo foi alterada.")
    text = example["texto"]
    for replacement in revision["substituicoes_texto"]:
        if text.count(replacement["anterior"]) != replacement["ocorrencias"]:
            raise RuntimeError("A transcrição-base do exemplo não corresponde à revisão registada.")
        text = text.replace(replacement["anterior"], replacement["novo"])
    example["texto"] = text
    example["versao"] = revision["versao"]
    indexed = {element["id"]: element for element in example["elementos"]}
    if not set(revision["elementos"]) <= set(indexed):
        raise RuntimeError("A revisão refere elementos inexistentes no exemplo-base.")
    for element_id, changes in revision["elementos"].items():
        indexed[element_id].update(deepcopy(changes))
    example["elementos"] = [Element.model_validate(element).model_dump() for element in example["elementos"]]
    return example


def example_content_sha256():
    content = json.dumps(load_example(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def example_provenance():
    """Compõe a rastreabilidade revista; nunca a acrescenta ao payload de análise."""
    metadata = json.loads(BASE_METADATA.read_text(encoding="utf-8"))
    revision = json.loads(METADATA.read_text(encoding="utf-8"))
    if hashlib.sha256(BASE_METADATA.read_bytes()).hexdigest() != revision["base"]["sha256"]:
        raise RuntimeError("Os metadados-base do exemplo foram alterados.")
    if hashlib.sha256(RESOURCE.read_bytes()).hexdigest() != revision["recurso_revisao"]["sha256"]:
        raise RuntimeError("O recurso revisto do exemplo não corresponde aos metadados.")
    if example_content_sha256() != revision["conteudo_sha256"]:
        raise RuntimeError("O conteúdo composto do exemplo não corresponde ao hash registado.")
    metadata["versao"], metadata["data"] = revision["versao"], revision["data"]
    metadata["conteudo_sha256"] = revision["conteudo_sha256"]
    metadata["fontes"].update(deepcopy(revision["fontes_adicionais"]))
    metadata["grupos"] = [deepcopy(revision["grupo_ct12a"]) if group["caso"] == "CT-12A" else group
                          for group in metadata["grupos"]]
    for group in metadata["grupos"]:
        if group["caso"] == "CT-13":
            group["adaptacoes"] = [revision["alteracoes_ct13"]["novo"] if value == revision["alteracoes_ct13"]["anterior"] else value
                                    for value in group["adaptacoes"]]
    metadata["limites"] = [value for value in metadata["limites"] if value not in revision["limites_removidos"]]
    metadata["limites"].extend(revision["limites_adicionados"])
    metadata["revisao_registada"] = deepcopy(revision["revisao_registada"])
    return metadata


# Compatibilidade com os testes técnicos de entrada que comparam o texto carregado.
TEXT = load_example()["texto"]


def load_demo(s):
    example = load_example()
    instrument, _ = from_text(example["texto"], example["titulo"])
    instrument.update(designacao=example["titulo"], versao=example["versao"],
                      estado=example["estado"], exemplo_id=example["id"])
    replace_document(s, instrument, example["elementos"])
    save_context(s, {k: {"valor": v, "disponibilidade": "Informado",
                        "visibilidade": "contexto interno fornecido à aplicação"}
                     for k, v in example["contexto"].items()}, [])
    # O motor já impede classificações integrais quando o alcance é localizado.
    # Nenhuma observação, categoria ou resposta esperada é pré-carregada.
    s["ambito"] = "recorte localizado"
    transition(s, "structure")
