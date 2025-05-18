import pytest

from src.application.pipeline.handlers import HistoryHandler
from src.application.pipeline.interfaces import HandlerContext, IHandler


class DummyNextHandler(IHandler):
    def handle(self, ctx: HandlerContext) -> HandlerContext:
        # Simula generación de respuesta por el assistant
        ctx.response_payload = {"text": "Respuesta simulada"}
        return ctx


def test_history_handler_appends_user_and_assistant_messages():
    # 1. Preparamos un contexto con historia previa
    initial_history = [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "¡Hola! ¿En qué puedo ayudarte?"}
    ]
    ctx = HandlerContext(raw_text="Quiero información", history=initial_history.copy())

    # 2. Construimos el handler con un Next que añade una respuesta
    dummy_next = DummyNextHandler()
    handler = HistoryHandler(next_handler=dummy_next)

    # 3. Ejecutamos
    result_ctx = handler.handle(ctx)
    # 4. Comprobamos que la historia se ha extendido
    assert len(result_ctx.history) == 4
    # El tercer elemento debe ser el mensaje del usuario actual
    assert result_ctx.history[2] == {"role": "user", "content": "Quiero información"}
    # El cuarto elemento debe ser la respuesta del assistant simulada
    assert result_ctx.history[3] == {"role": "assistant", "content": "Respuesta simulada"}


def test_history_handler_handles_empty_initial_history():
    # 1. Sin historia previa
    ctx = HandlerContext(raw_text="¿Cómo funcionan las becas?", history=[])
    dummy_next = DummyNextHandler()
    handler = HistoryHandler(next_handler=dummy_next)

    # 2. Ejecutamos
    result_ctx = handler.handle(ctx)

    # 3. Debe tener dos entradas: user y assistant
    assert len(result_ctx.history) == 2
    assert result_ctx.history[0] == {"role": "user", "content": "¿Cómo funcionan las becas?"}
    assert result_ctx.history[1] == {"role": "assistant", "content": "Respuesta simulada"}

def test_history_handler_truncates_history():
    # 1. Preparamos un contexto con historia previa
    initial_history = [
        {"role": "user", "content": f"Mensaje {i}"} for i in range(10)
    ]
    ctx = HandlerContext(raw_text="Último mensaje", history=initial_history.copy())
    # 2. Construimos el handler con un Next que añade una respuesta
    dummy_next = DummyNextHandler()
    handler = HistoryHandler(next_handler=dummy_next, max_history=5)

    # 3. Ejecutamos
    result_ctx = handler.handle(ctx)

    # 4. Comprobamos que la historia se ha truncado a las últimas 5 entradas
    assert len(result_ctx.history) == 5
    assert result_ctx.history[0] == {"role": "user", "content": f"Mensaje {7}"}