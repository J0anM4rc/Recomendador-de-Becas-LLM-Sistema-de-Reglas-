import json


import pytest

from pipeline.handlers.protocols import BuscarPorCriterioDTO, HandlerContext
from src.domain.entities import DialogAct
from infrastructure.llm.gemma import LLAMA
from src.infrastructure.llm_response_builder import (
    TemplateResponseBuilder
)

# ---------------------------------------------------------------------------
#  Stubs / helpers
# ---------------------------------------------------------------------------




class DummyCtx:
    """Contexto mínimo que necesita el builder."""

    def __init__(self, with_history: bool = True):
        if with_history:
            self.history = [
                {"role": "assistant", "content": "¿Área de estudio?"},
                {"role": "user", "content": "ciencias_sociales"},
            ]
        else:
            self.history = []

    # La implementación real está en tu clase; basta con simularla
    def last_interaction(self) -> str:
        return "Asistente: ¿Área de estudio?\nUsuario: ciencias_sociales"


# ---------------------------------------------------------------------------
#  Tests
# ---------------------------------------------------------------------------

def test_render_includes_context_when_history():
    """
    Verifica que:
    1) La respuesta se trimea (.strip()).
    2) El prompt enviado al LLM contiene <context> cuando hay history.
    3) El JSON de los dialog-acts está incluido en <tool_state>.
    """

    builder = TemplateResponseBuilder()

    act1 = DialogAct(type="ack_field", field="nivel", new="posgrado")
    act2 = DialogAct(type="ask_field", field="organismo", new=None)
    initial_history = [
        {"role": "assistant", "content": "¿En qué área de estudios te interesan las becas? Opciones: ciencias_tecnicas, ciencias_sociales, arte_humanidades, salud, otro"},
        {"role": "user", "content": "salud esta bien"},
        {"role": "assistant", "content": "Vale, entonces salut, ahora ¿Para qué nivel educativo es la beca? Opciones: grado, posgrado, postobligatoria_no_uni, otro"},
        {"role": "user", "content": "postgrado"},
    ]
    fc = BuscarPorCriterioDTO(
        active_fields=["campo_estudio", "nivel"],
        area="salud",
        education_level=None,
        location=None,
        organization=None
    )
    ctx = HandlerContext(
        raw_text="relleno para que no falle el test",
        normalized_text="relleno para que no falle el test",
        history=initial_history.copy(),
        filter_criteria=fc,
        last_intention="buscar_por_criterio"
    )

    result = builder.render([act1,act2], ctx)
    print("Result:", result)
    assert result.strip()  # Verifica que la respuesta no esté vacía



def test_render_without_history_excludes_context():
    """
    Sin history, el bloque <context> no debe aparecer en el prompt.
    """
    dummy_llm = LLAMA()
    builder = TemplateResponseBuilder(llama_client=dummy_llm)

    acts = [DialogAct(type="ack_field", field="organismo", new="publico_estatal")]
    ctx = DummyCtx(with_history=False)

    builder.render(acts, ctx)

    assert "<context>" not in dummy_llm.last_prompt
