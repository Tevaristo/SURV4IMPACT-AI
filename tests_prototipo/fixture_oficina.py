"""Fixture técnica anterior preservada; não é o exemplo disponibilizado na aplicação."""
from prototipo.extraction import from_text
from prototipo.models import Element
from prototipo.state import replace_document, save_context

TEXT = """Questionário de apreciação da oficina de escrita — versão de demonstração 1, 09-09-2026.
Convite e instruções apresentados ao respondente:
Pretendemos conhecer a satisfação com a oficina realizada em 8 de setembro de 2026 e recolher
sugestões para melhorar futuras oficinas. A participação é voluntária. Não se pede o seu nome
ou contacto. A equipa de avaliação consulta as respostas e divulga apenas resultados agregados;
comentários livres serão revistos para retirar referências que identifiquem pessoas.
Responda apenas sobre essa oficina. Pode escolher Não sei ou Prefiro não responder.
P1. Participou na oficina de escrita de 8 de setembro de 2026?
Sim: prossiga para P2. Não / Prefiro não responder: termine o questionário.
P2. Qual o seu grau de satisfação com a clareza das explicações nessa oficina?
Muito insatisfeito; Insatisfeito; Nem satisfeito nem insatisfeito; Satisfeito; Muito satisfeito;
Não sei; Prefiro não responder. Escolha uma opção.
P3. Que sugestão gostaria de deixar para melhorar futuras oficinas? Resposta livre, facultativa.
Não inclua nomes ou outros dados que identifiquem pessoas. Obrigado pela participação.
"""


def load_demo(s):
    instrument, _ = from_text(TEXT, "Instrumento sintético de demonstração")
    instrument.update(designacao="Apreciação da oficina de escrita", versao="demo 1 — 09-09-2026", estado="em preparação")
    elements = [Element(id="INTRO", texto=TEXT.split("P1.")[0], localizacao="introdução", formato="instrução", instrucoes="Aplicável a P1–P3", instrucao_aplica_a=["P1", "P2", "P3"], restricoes="nenhuma").model_dump(),
        Element(id="P1", texto="Participou na oficina de escrita de 8 de setembro de 2026?", localizacao="P1", formato="escolha única", opcoes=["Sim", "Não", "Prefiro não responder"], condicoes_destinos="Sim → P2; Não / Prefiro não responder → fim", restricoes="uma opção").model_dump(),
        Element(id="P2", texto="Qual o seu grau de satisfação com a clareza das explicações nessa oficina?", localizacao="P2", formato="escolha única", opcoes=["Muito insatisfeito", "Insatisfeito", "Nem satisfeito nem insatisfeito", "Satisfeito", "Muito satisfeito", "Não sei", "Prefiro não responder"], instrucoes="Responda apenas sobre a oficina de 8 de setembro de 2026. Escolha uma opção.", restricoes="uma opção").model_dump(),
        Element(id="P3", texto="Que sugestão gostaria de deixar para melhorar futuras oficinas?", localizacao="P3", formato="livre", instrucoes="Resposta livre, facultativa. Não inclua nomes ou outros dados que identifiquem pessoas.", restricoes="nenhuma").model_dump()]
    replace_document(s, instrument, elements)
    values = {"público/destinatários": "Adultos inscritos na oficina, com ou sem participação efetiva",
        "função/perfil do respondente": "Participante, leitor de português corrente",
        "unidade de resposta": "A própria participação na oficina de 8-09-2026",
        "modo previsto": "online", "finalidade": "Melhorar a clareza das explicações em oficinas futuras",
        "objetivos/questões de avaliação": "Conhecer satisfação com a clareza e recolher sugestões; P1 filtra participação, P2 mede satisfação e P3 recolhe sugestões",
        "dimensões principais": "Satisfação com clareza das explicações; sugestões de melhoria",
        "momento da recolha": "Dia seguinte à oficina (09-09-2026)", "estado dos projetos/intervenções": "Oficina concluída"}
    save_context(s, {k: {"valor": v, "disponibilidade": "Informado", "visibilidade": "contexto interno fornecido à aplicação"} for k, v in values.items()}, [])
    s["stage"] = "structure"
