from __future__ import annotations

from .models import Question, Questionnaire


def demo_questionnaire() -> Questionnaire:
    questions = [
        Question(
            id="question-1",
            label="Q1",
            text="Nos últimos 12 meses, recorreu aos serviços de apoio do programa?",
            section="Experiência com o programa",
            options=["Sim", "Não"],
            question_type="sim/não",
            word_count=11,
            source="Exemplo integrado",
        ),
        Question(
            id="question-2",
            label="Q2",
            text="Como avalia a informação e o apoio técnico disponibilizados pelo programa e em que medida considera que contribuíram para melhorar simultaneamente a eficiência da sua organização e a qualidade dos serviços prestados?",
            section="Experiência com o programa",
            options=[
                "1 — Muito negativo",
                "2 — Negativo",
                "3 — Neutro",
                "4 — Positivo",
                "5 — Muito positivo",
            ],
            question_type="escala",
            word_count=32,
            source="Exemplo integrado",
        ),
        Question(
            id="question-3",
            label="Q3",
            text="Não considera que o procedimento não foi demasiado complexo?",
            section="Procedimentos",
            options=["Discordo totalmente", "Discordo", "Concordo", "Concordo totalmente"],
            question_type="escala",
            word_count=9,
            source="Exemplo integrado",
        ),
        Question(
            id="question-4",
            label="Q4",
            text="Com que frequência utiliza a plataforma?",
            section="Procedimentos",
            options=["Nunca", "Raramente", "Às vezes", "Frequentemente", "Sempre"],
            question_type="escala",
            word_count=7,
            source="Exemplo integrado",
        ),
        Question(
            id="question-5",
            label="Q5",
            text="Se respondeu ‘Não’ à pergunta 1, passe para a pergunta 7.",
            section="Procedimentos",
            options=["Sim", "Não"],
            question_type="sim/não",
            word_count=11,
            routing_text="Se respondeu ‘Não’ à pergunta 1, passe para a pergunta 7.",
            source="Exemplo integrado",
        ),
        Question(
            id="question-6",
            label="Q6",
            text="Que melhorias recomenda?",
            section="Sugestões",
            options=[],
            question_type="aberta",
            word_count=3,
            source="Exemplo integrado",
            required=True,
        ),
        Question(
            id="question-7",
            label="Q7",
            text="Indique quaisquer outros comentários que considere relevantes.",
            section="Sugestões",
            options=[],
            question_type="aberta",
            word_count=7,
            source="Exemplo integrado",
        ),
    ]
    return Questionnaire(
        title="Questionário demonstrativo SURV4IMPACT",
        questions=questions,
        sections=["Experiência com o programa", "Procedimentos", "Sugestões"],
        instructions=[
            "Responda às perguntas seguintes com base na sua experiência.",
            "Se respondeu ‘Não’ à pergunta 1, passe para a pergunta 7.",
        ],
        raw_text="\n".join(question.text for question in questions),
        source_name="exemplo_integrado",
    )

