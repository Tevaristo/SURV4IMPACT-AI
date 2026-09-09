from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import uuid4

from .models import Element, Category
from .norma import CRITERIOS, provenance

STAGES = {"intake": "Instrumento e contexto", "structure": "Confirmar representação", "review": "Apreciação documental", "clarifications": "Esclarecimentos e ações", "decisions": "Decisão humana", "report": "Relatório"}


def now():
    return datetime.now(timezone.utc).isoformat()


def fingerprint(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def new_session():
    return {"id": uuid4().hex, "stage": "intake", "instrumento": {}, "contexto": {},
            "documentos": [], "representacao": [], "confirmada": False, "revisao": 0,
            "verificacoes": {}, "propostas": {}, "decisoes": {}, "pedidos": [],
            "acoes": {}, "historico": [], "norma": provenance(), "api": {},
            "ambito": "integral", "rastreabilidade_substituicao": {}, "criada": now()}


def transition(s, target):
    if target not in STAGES:
        raise ValueError("Destino de navegação inválido.")
    if target != "intake" and not s["instrumento"]:
        raise ValueError("Identifique primeiro o instrumento.")
    if target == "review" and not s["confirmada"]:
        raise ValueError("Confirme a representação necessária antes de iniciar a análise.")
    s["stage"] = target


def replace_document(s, instrument, representation):
    fresh = new_session()
    fresh["instrumento"] = deepcopy(instrument)
    fresh["representacao"] = [Element.model_validate(e).model_dump() for e in representation]
    s.clear()
    s.update(fresh)


def invalidate(s, changed, reason):
    affected = []
    for rule, v in list(s["verificacoes"].items()):
        deps = set(v["dependencias"])
        if "*" in changed or "*" in deps or deps.intersection(changed):
            affected.append(rule)
            s["historico"].append({"data": now(), "tipo": reason, "regra": rule, "resultado_retirado": s["verificacoes"].pop(rule)})
            for p in s["pedidos"]:
                if p["regra"] == rule and p["estado"] == "pendente":
                    p["estado"] = "substituído por reapreciação"
            for action in s["acoes"].values():
                if action["regra"] == rule:
                    action["estado"] = "retirada para reapreciação"
    criteria = {r[:4] for r in affected}
    for c in criteria:
        for key in ("propostas", "decisoes"):
            if c in s[key]:
                s["historico"].append({"data": now(), "tipo": reason, key: s[key].pop(c)})
    return affected


def save_representation(s, elements, confirmed, reason="correção da representação"):
    parsed = [Element.model_validate(e).model_dump() for e in elements]
    if not parsed or any(not e["id"].strip() or not e["texto"].strip() or not e["localizacao"].strip() for e in parsed):
        raise ValueError("Cada elemento precisa de identificador, texto e localização.")
    if len({e["id"] for e in parsed}) != len(parsed):
        raise ValueError("Os identificadores devem ser únicos.")
    # Normaliza também sessões anteriores à estruturação dos limites para que
    # a migração de esquema, por si só, não invalide resultados dependentes.
    old = {e["id"]: Element.model_validate(e).model_dump() for e in s["representacao"]}
    current = {e["id"]: e for e in parsed}
    changed = {k for k in old.keys() | current.keys() if old.get(k) != current.get(k)}
    if list(old) != list(current):
        changed.add("ordem")
    if set(old) != set(current):
        changed.add("estrutura")
    affected = invalidate(s, changed, reason)
    if changed:
        s["revisao"] += 1
        s["historico"].append({"data": now(), "tipo": reason, "elementos": sorted(changed),
                               "antes": s["representacao"], "depois": parsed, "verificacoes_a_repetir": affected})
    s["representacao"] = parsed
    s["confirmada"] = bool(confirmed)
    s["confirmacao"] = {"data": now(), "hash": fingerprint(parsed), "explicita": bool(confirmed)}
    if not confirmed:
        s["propostas"].clear()
        s["decisoes"].clear()


def save_context(s, context, documents):
    changed = {"contexto:" + k for k in s["contexto"].keys() | context.keys() if s["contexto"].get(k) != context.get(k)}
    if s["documentos"] != documents:
        changed.add("documentos")
    invalidate(s, changed, "contexto/documentos atualizados")
    s["contexto"], s["documentos"] = deepcopy(context), deepcopy(documents)


def register_batch(s, batch):
    for v in batch.verificacoes:
        value = v.model_dump()
        value["dependencias"] = sorted(set(value["dependencias"]) | {"estrutura"})
        # Herança explícita de instruções: mudar uma instrução partilhada afeta os seus itens.
        for element in s["representacao"]:
            if set(element["instrucao_aplica_a"]).intersection(value["dependencias"]):
                value["dependencias"] = sorted(set(value["dependencias"]) | {element["id"]})
        for p in s["pedidos"]:
            if p["regra"] == v.regra and p["estado"] == "respondido — por reapreciar":
                p["estado"] = "respondido — reapreciado"
        s["verificacoes"][v.regra] = value
        s["propostas"].pop(v.regra[:4], None)
        s["decisoes"].pop(v.regra[:4], None)
        for i, obs in enumerate(v.observacoes):
            oid = f"{v.regra}:{i}:{fingerprint(obs.model_dump())[:12]}"
            if obs.informacao_adicional and not any(p["id"] == oid for p in s["pedidos"]):
                s["pedidos"].append({"id": oid, "regra": v.regra, "pergunta": obs.informacao_adicional,
                    "justificacao": obs.justificacao, "indispensavel": obs.indispensavel_ao_nucleo,
                    "origem": obs.tipo_situacao, "estado": "pendente", "respostas": [], "observacao": obs.model_dump()})
            if obs.acao != "nenhuma ação":
                previous = s["acoes"].get(oid)
                if previous and previous.get("estado") == "retirada para reapreciação":
                    s["historico"].append({"data": now(), "tipo": "ação reapreciada", "acao_anterior": deepcopy(previous)})
                    del s["acoes"][oid]
                s["acoes"].setdefault(oid, {"regra": v.regra, "elemento": obs.elemento, "estado": "proposta atual",
                    "alteracao_necessaria": obs.alteracao_necessaria, "proposta_redacao": obs.proposta_redacao,
                    "aceite": False, "incorporada": False, "versao_revista": "", "localizacao": ""})


def answer(s, pid, text, visibility, unavailable=False, close=False):
    p = next(p for p in s["pedidos"] if p["id"] == pid)
    if not text.strip():
        raise ValueError("Registe a resposta ou a declaração de indisponibilidade.")
    p["respostas"].append({"data": now(), "texto": text, "visibilidade": visibility,
                            "indisponivel": unavailable, "fecho_explicito": close})
    p["estado"] = "fechado com limites" if unavailable or close else "respondido — por reapreciar"
    invalidate(s, {"pedido:" + pid}, "resposta a esclarecimento dependente")
    # Uma resposta afeta apenas a verificação que a solicitou; preserva o pedido e o histórico.
    rule = p["regra"]
    if rule in s["verificacoes"]:
        s["historico"].append({"data": now(), "tipo": "resposta recebida", "resultado_retirado": s["verificacoes"].pop(rule)})
    for action in s["acoes"].values():
        if action["regra"] == rule:
            action["estado"] = "retirada para reapreciação"
    s["propostas"].pop(rule[:4], None)
    s["decisoes"].pop(rule[:4], None)


def decide(s, criterion, category, rationale, reviewer, explicit):
    p = s["propostas"].get(criterion)
    if not s["confirmada"] or not p or not p["categoria"]:
        raise ValueError("É necessária uma proposta concluída com representação confirmada.")
    if not explicit or not rationale.strip() or not reviewer.strip():
        raise ValueError("Registe uma decisão humana expressa, responsável e fundamentação.")
    if category not in Category.__args__:
        raise ValueError("Categoria inválida.")
    if category == "Não Aplicável" and (criterion != "D2.6" or not no_response_object(s)):
        raise ValueError("A dispensa D2.6 exige exclusivamente respostas livres confirmadas, sem restrições.")
    s["decisoes"][criterion] = {"categoria": category, "fundamentacao": rationale, "responsavel": reviewer,
        "expressa": True, "data": now(), "proposta_hash": fingerprint(p), "representacao_hash": fingerprint(s["representacao"])}


def completed(s):
    return s["ambito"] == "integral" and s["confirmada"] and all(c in s["decisoes"] and c in s["propostas"] and s["propostas"][c]["categoria"] and s["decisoes"][c]["proposta_hash"] == fingerprint(s["propostas"][c]) for c in CRITERIOS)


def no_response_object(s):
    elements = [Element.model_validate(e).model_dump() for e in s["representacao"] if e["formato"] != "instrução"]
    return bool(elements) and all(
        e["formato"] == "livre" and not e["opcoes"] and not e["colunas"]
        and e["regra_selecao"] == "Sem limite explícito"
        for e in elements
    )
