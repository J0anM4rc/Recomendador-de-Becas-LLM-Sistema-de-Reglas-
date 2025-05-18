# tests/integration/test_classify_all_real_llm.py

import os
import pytest
from src.infrastructure.llm_interface import LLAMA
from src.infrastructure.intention_classifier import IntentionClassifier

@pytest.fixture(scope="session")
def real_classifier():
    # Asegúrate de poner aquí la ruta donde tienes tu modelo LLAMA 3.2
    llm = LLAMA()
    return IntentionClassifier(llm=llm)

@pytest.mark.parametrize("msg,expected_intents", [
    ("Quiero buscar becas para Magisterio", {"buscar_por_criterio"}),
    ("1234", {"general_qa"}),
    ("¿Qué significa financiación completa?", {"explicar_termino"}),
    ("atrás", {"navegacion_conversacion"}),
])
def test_classify_all_real_llm(real_classifier, msg, expected_intents):
    """
    Lanza classify_all contra mensajes de muestra y comprueba que la intención
    está entre las esperadas (permitimos cierta flexibilidad).
    """
    out = real_classifier.classify(msg)
    assert "intencion" in out
    assert out["intencion"] in expected_intents, (
        f"Mensaje: {msg!r} → obtuvo intención {out['intencion']!r}, "
        f"pero esperaba una de {expected_intents}"
    )
    # # Debe devolver siempre un dict filters/navigation/confirmation/error
    # for key in ("filters","navigation","confirmation","error"):
    #     assert key in out

    # Si es búsqueda por nombre, el filtro "name" no debe ser None
    if out["intencion"] == "buscar_por_criterio":
        assert out["filters"].get("name"), f"Esperado filtro name para {msg!r}."

    # # Si es búsqueda por código, debe mapear code
    # if out["intencion"] == "buscar_por_codigo":
    #     code = out["filters"].get("code")
    #     assert code is not None and code.isdigit(), f"Esperaba código para {msg!r}."

