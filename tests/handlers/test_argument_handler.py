# tests/test_argument_classifier.py
import pytest
from typing import Any, Dict, List, Optional

from src.infrastructure.prolog_connector import ScholarshipRepository
from src.infrastructure.llm_interface import LLAMA
from src.infrastructure.argument_classifier import ArgumentClassifier



# -





# --- FIXTURE ----------------------------------------------------------------

@pytest.fixture
def classifier():
    # Lo inicializamos con stubs; usamos un LLM que por defecto no hace nada
    llm = LLAMA()
    return ArgumentClassifier(llm=llm)


# --- TESTS -------------------------------------------------------------------

def test_guided_flow_chosen_option(classifier):
    # 1) simulamos que interpret_guided_response detecta opción
    result = classifier.classify(
        message="Cuantas preguntas quedan?",
        current_question="¿En qué área de estudios te interesan las becas?",
        available_options=["ciencias_tecnicas", "ciencias_sociales", "arte_humanidades", "salud", "otro", "cualquiera"],
        is_confirming=False
    )
    print(result)
    assert result == {
        "chosen_option": "cualquiera",
        "navigation_intent": None,
        "argumento": None
    }


def test_guided_flow_navigation(classifier, monkeypatch):
    # 2) simulamos que quiere saltar
    monkeypatch.setattr(
        classifier,
        "interpret_guided_response",
        lambda msg, q, opts: {"chosen_option": None, "navigation_intent": "saltar_omitir"}
    )

    result = classifier.classify(
        message="no me importa",
        current_question="¿Nivel?",
        available_options=["grado", "master"],
        is_confirming=False
    )
    assert result == {
        "chosen_option": None,
        "navigation_intent": "saltar_omitir",
        "argumento": None
    }


def test_confirmation_flow(classifier, monkeypatch):
    # 3) simulamos confirmación
    monkeypatch.setattr(
        classifier,
        "interpret_confirmation_response",
        lambda msg: "si"
    )

    result = classifier.classify(
        message="sí, correcto",
        current_question=None,
        available_options=None,
        is_confirming=True
    )
    assert result == {
        "intencion": "respuesta_confirmacion",
        "confirmation_status": "si",
        "argumento": None
    }


def test_fallback_intent(classifier, monkeypatch):
    # 4) simulamos clasificación de intención genérica
    monkeypatch.setattr(
        classifier,
        "classify_intent",
        lambda msg: "info_beca"
    )

    result = classifier.classify(
        message="¿Qué sabes de beca1?",
        current_question=None,
        available_options=None,
        is_confirming=False
    )
    assert result == {
        "intencion": "info_beca",
        "argumento": None
    }
