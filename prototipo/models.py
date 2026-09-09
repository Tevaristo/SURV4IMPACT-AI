from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Criterion = Literal["D2.3", "D2.4", "D2.6"]
Category = Literal["Cumpre", "Cumpre parcialmente", "Não cumpre/Não evidenciado", "Não Aplicável"]
Situation = Literal["adequação documental", "problema demonstrado", "dúvida de extração ou representação", "documentação/contexto não disponibilizado", "esclarecimento necessário", "verificação posterior"]
Action = Literal["nenhuma ação", "correção necessária", "pedido de esclarecimento", "aperfeiçoamento facultativo", "fecho com limites"]
Status = Literal["Por concluir", "A aguardar esclarecimento", "A aguardar validação da extração", "Concluída", "Fechada com limites"]
SelectionRule = Literal[
    "Não aplicável",
    "Não foi possível confirmar",
    "Uma única resposta",
    "Número exato de respostas",
    "Até ao máximo indicado",
    "Pelo menos o mínimo indicado",
    "Entre o mínimo e o máximo indicados",
    "Sem limite explícito",
    "Outra condição indicada no questionário",
]
SELECTION_RULES = list(SelectionRule.__args__)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Element(Strict):
    id: str
    texto: str
    localizacao: str
    formato: str = "não confirmado"
    opcoes: list[str] = Field(default_factory=list)
    subitens: list[str] = Field(default_factory=list)
    linhas: list[str] = Field(default_factory=list)
    colunas: list[str] = Field(default_factory=list)
    instrucoes: str = ""
    instrucao_aplica_a: list[str] = Field(default_factory=list)
    condicoes_destinos: str = ""
    regra_selecao: SelectionRule = "Não foi possível confirmar"
    numero_minimo: int | None = Field(default=None, ge=0)
    numero_maximo: int | None = Field(default=None, ge=0)
    outra_condicao_resposta: str = ""
    # Campo textual conservado para compatibilidade com sessões, recursos,
    # relatórios e consumidores anteriores à estruturação dos limites.
    restricoes: str = "não confirmadas"

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_limits(cls, value):
        """Converte apenas valores legados inequívocos; conserva os restantes literalmente."""
        if not isinstance(value, dict) or "regra_selecao" in value:
            return value
        data = dict(value)
        raw = str(data.get("restricoes", "não confirmadas") or "").strip()
        canonical = {
            "": "Não foi possível confirmar",
            "não confirmadas": "Não foi possível confirmar",
            "não confirmado": "Não foi possível confirmar",
            "não aplicável": "Não aplicável",
            "nenhuma": "Sem limite explícito",
            "sem limite explícito": "Sem limite explícito",
            "uma resposta": "Uma única resposta",
        }
        data["regra_selecao"] = canonical.get(raw.casefold(), "Outra condição indicada no questionário")
        if data["regra_selecao"] == "Uma única resposta":
            data["numero_minimo"] = 1
            data["numero_maximo"] = 1
        elif data["regra_selecao"] == "Outra condição indicada no questionário":
            data["outra_condicao_resposta"] = raw
        return data

    @model_validator(mode="after")
    def validate_and_sync_limits(self):
        """Valida coerência editorial e mantém a representação textual compatível."""
        rule = self.regra_selecao
        minimum, maximum = self.numero_minimo, self.numero_maximo
        other = self.outra_condicao_resposta.strip()
        needs_minimum = rule in ("Uma única resposta", "Número exato de respostas", "Pelo menos o mínimo indicado", "Entre o mínimo e o máximo indicados")
        needs_maximum = rule in ("Uma única resposta", "Número exato de respostas", "Até ao máximo indicado", "Entre o mínimo e o máximo indicados")
        if needs_minimum and minimum is None:
            raise ValueError("A regra de seleção escolhida exige um número mínimo.")
        if needs_maximum and maximum is None:
            raise ValueError("A regra de seleção escolhida exige um número máximo.")
        if not needs_minimum and minimum is not None:
            raise ValueError("A regra de seleção escolhida não utiliza um número mínimo.")
        if not needs_maximum and maximum is not None:
            raise ValueError("A regra de seleção escolhida não utiliza um número máximo.")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("O número mínimo não pode ser superior ao número máximo.")
        if rule == "Uma única resposta" and (minimum != 1 or maximum != 1):
            raise ValueError("Uma única resposta exige mínimo 1 e máximo 1.")
        if rule == "Número exato de respostas" and minimum != maximum:
            raise ValueError("No número exato de respostas, o mínimo e o máximo devem ser iguais.")
        if rule == "Outra condição indicada no questionário" and not other:
            raise ValueError("Transcreva a outra condição de resposta indicada no questionário.")
        if rule != "Outra condição indicada no questionário" and other:
            raise ValueError("A outra condição de resposta só se aplica à opção correspondente.")

        if rule == "Não aplicável":
            self.restricoes = "não aplicável"
        elif rule == "Não foi possível confirmar":
            self.restricoes = "não confirmadas"
        elif rule == "Uma única resposta":
            self.restricoes = "uma resposta"
        elif rule == "Número exato de respostas":
            self.restricoes = f"exatamente {minimum} respostas"
        elif rule == "Até ao máximo indicado":
            self.restricoes = f"máximo de {maximum} respostas"
        elif rule == "Pelo menos o mínimo indicado":
            self.restricoes = f"mínimo de {minimum} respostas"
        elif rule == "Entre o mínimo e o máximo indicados":
            self.restricoes = f"entre {minimum} e {maximum} respostas"
        elif rule == "Sem limite explícito":
            self.restricoes = "nenhuma"
        else:
            self.outra_condicao_resposta = other
            self.restricoes = other
        return self


class Observation(Strict):
    criterio: Criterion
    regra_origem: str
    elemento: str
    evidencia_textual: str
    localizacao: str
    contexto_utilizado: str
    observacao: str
    justificacao: str
    consequencia_plausivel: str
    alcance: str
    tipo_situacao: Situation
    acao: Action
    estado: Status
    informacao_adicional: str
    limites_inferencias_proibidas: str
    indispensavel_ao_nucleo: bool
    alteracao_necessaria: str
    proposta_redacao: str
    dependencias: list[str]


class Verification(Strict):
    regra: str
    estado: Status
    observacoes: list[Observation]
    fundamento: str
    dependencias: list[str]
    pendencia_metodologica: str


class ReviewBatch(Strict):
    verificacoes: list[Verification]


class CriterionProposal(Strict):
    criterio: Criterion
    estado: Status
    categoria: Category | None
    evidencia_adequacao: str
    lacuna_motivo: str
    consequencia: str
    alcance: str
    atenuantes: str
    efeito_conjunto: str
    justificacao: str
    acao: str
    limites: str
