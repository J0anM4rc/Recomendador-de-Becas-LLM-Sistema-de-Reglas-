# tests/test_argument_classifier.py
import pytest
from typing import Any, Dict, List, Optional

from src.application.pipeline.handlers import CriteriaSearchHandler
from src.application.pipeline.interfaces import BuscarPorCriterioDTO, HandlerContext, IHandler
from src.infrastructure.prolog_connector import ScholarshipRepository
from src.infrastructure.argument_classifier import ArgumentClassifier

class DummyNextHandler(IHandler):
    def handle(self, ctx: HandlerContext) -> HandlerContext:
        ctx.response_payload = {"text": "dummy response"}
        return ctx

@pytest.fixture
def handler():
    return CriteriaSearchHandler(next_handler=DummyNextHandler())





# --- TESTS -------------------------------------------------------------------
@pytest.mark.parametrize("user_input, action, field, value", [
    ("posgrado", "select", "nivel", "posgrado"),
    ("la tercera opcion", "select", "nivel", "postobligatoria_no_uni"),
    ("a la que pertenezca ingenieria informatica","select", "nivel", "grado"),
    ("la que sea","select", "nivel", "cualquiera"),
    ("otro","select", "nivel", "otro"),
    
])
def test_guided_flow_select_answers(handler, user_input, action, field, value):
    
    initial_history = [
        {"role": "assistant", "content": "¿En qué área de estudios te interesan las becas? Opciones: ciencias_tecnicas, ciencias_sociales, arte_humanidades, salud, otro"},
        {"role": "user", "content": "salud esta bien"},
        {"role": "assistant", "content": "Vale, entonces salut, ahora ¿Para qué nivel educativo es la beca? Opciones: grado, posgrado, postobligatoria_no_uni, otro"},
        {"role": "user", "content": user_input},
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
    ctx = handler.handle(ctx)
    criteria = ctx.filter_criteria
    
    assert criteria.education_level == value

@pytest.mark.parametrize("user_input, action, field, value", [
    ("Espera, cambia la anterior a ciencias sociales", "modify", "campo_estudio", "ciencias_sociales"),
    ("Pon el anterior en ciencias_sociales", "modify", "campo_estudio", "ciencias_sociales"),
    ("Pon la anterior en cualquiera", "modify", "campo_estudio", "cualquiera"), # No funciona
    ("Elimina la anterior", "modify", "campo_estudio", None), # No funciona
    
])
def test_guided_flow_modify_answers(handler, user_input, action, field, value):
    
    initial_history = [
        {"role": "assistant", "content": "¿En qué área de estudios te interesan las becas? Opciones: ciencias_tecnicas, ciencias_sociales, arte_humanidades, salud, otro"},
        {"role": "user", "content": "salud esta bien"},
        {"role": "assistant", "content": "Vale, entonces salut, ahora ¿Para qué nivel educativo es la beca? Opciones: grado, posgrado, postobligatoria_no_uni, otro"},
        {"role": "user", "content": user_input},
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
    ctx = handler.handle(ctx)
    criteria = ctx.filter_criteria
    
    assert criteria.area == value
    
@pytest.mark.parametrize("user_input, action, field, value", [
    ("Que cubre una beca parcial?", None, None, None),
    ("No, quiero buscar una beca en concreto", None, None, None),
    
])
def test_guided_flow_none(handler, user_input, action, field, value):
    
    initial_history = [
        {"role": "assistant", "content": "¿En qué área de estudios te interesan las becas? Opciones: ciencias_tecnicas, ciencias_sociales, arte_humanidades, salud, otro"},
        {"role": "user", "content": "salud esta bien"},
        {"role": "assistant", "content": "Vale, entonces salut, ahora ¿Para qué nivel educativo es la beca? Opciones: grado, posgrado, postobligatoria_no_uni, otro"},
        {"role": "user", "content": user_input},
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
    ctx = handler.handle(ctx)
    criteria = ctx.filter_criteria
    
    assert criteria.area == None


    
@pytest.mark.parametrize("user_input", [
    # ("Si, adelante"),
    ("No, cambia el campo de estudio a ciencias sociales"),
    # ("Podré buscar con otros criterios más adelante?"),
    
]) 
def test_confirmation_flow(handler, user_input):
    
    initial_history = [
        {"role": "user", "content": user_input},
    ]
    fc = BuscarPorCriterioDTO(
        area="salud",
        education_level="libertad",
        location="fraternidad",
        organization="solidaridad"
    )

    ctx = HandlerContext(
        raw_text="relleno para que no falle el test",
        normalized_text="relleno para que no falle el test",
        history=initial_history.copy(),
        filter_criteria=fc,
        last_intention="buscar_por_criterio"
    )
    
    ctx = handler.handle(ctx)
    assert ctx

