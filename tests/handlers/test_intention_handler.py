import pytest
from src.application.pipeline.handlers import IntentHandler
from src.application.pipeline.interfaces import HandlerContext, IHandler

class DummyNextHandler(IHandler):
    def handle(self, ctx: HandlerContext) -> HandlerContext:
        ctx.response_payload = {"text": "dummy response"}
        return ctx

@pytest.fixture
def handler():
    return IntentHandler(next_handler=DummyNextHandler())

@pytest.mark.parametrize("user_input, expected_intent_options", [
    ("Quiero encontrar una beca para estudiar Ingenieria Informatica el año que viene.", {"guiado"}),
    ("Estoy interesado en optar a una beca universitaria, ¿me ayudas a buscar opciones?", {"guiado"}),
    ("Busco ayudas económicas para estudiar un máster", {"guiado"}),
    ("Necesito apoyo financiero para mis estudios", {"guiado"}),
    ("¿Me podrías recomendar becas internacionales para postgrado?", {"guiado"}),
    ("Quiero explorar becas de movilidad Erasmus, ¿me guías?", {"guiado"}),
    ("Estoy buscando becas para estudiantes de ciencias, ¿qué programas existen?", {"guiado"}),
    ("¿Cómo puedo encontrar becas para investigación en biología?", {"guiado"}),
    ("Me gustaría recibir información sobre becas para estudios de arte, ¿me ayudas a buscarlas?", {"guiado"}),
    ("Deseo acceder a becas de tecnología, ¿puedes ayudarme a buscar algunas?", {"guiado"}),
    ("¿Podrías ayudarme a filtrar becas según mi perfil académico?", {"guiado"}),
    ("Necesito encontrar becas para estudiantes con necesidad económica, ¿me orientas?", {"guiado"}),
    ("Voy a empezar un FP superior, ¿puedo optar a alguna beca?", {"guiado"}),
    ("Este año me gustaría solicitar alguna beca.", {"guiado"}),
])
def test_intention_criterio(handler, user_input, expected_intent_options):
    ctx = HandlerContext(raw_text=user_input, normalized_text=user_input)
    ctx = handler.handle(ctx)
    assert ctx.intention == "buscar_por_criterio"
    

@pytest.mark.parametrize("user_input", [
    ("Háblame de la beca del MEC."),
    ("Me interesa la beca CONACYT Nacional y también la Eiffel"),
    ("¿Qué sabes sobre la beca de La Caixa para posgrados?"),
    ("¿Qué sabes de beca_mec_general?"),
    ("No quiero la beca de transporte de la GV, sino la de excelencia de allí."), # Negation + specific
    ("Busco info de la beca de Santander para aprender inglés."),
    ("¿La beca de excelencia de la Generalitat Valenciana sigue abierta?"),
    ("¿Qué onda con la beca OEA?")
])
def test_intention_info(handler, user_input):
    ctx = HandlerContext(raw_text=user_input, normalized_text=user_input)
    ctx = handler.handle(ctx)
    assert ctx.intention == "info_beca"


@pytest.mark.parametrize("user_input", [
    ("La primera"),
    ("tecnicas"),
    ("Espera, cambia la anterior a completa"),
    ("quiero modificar la anterior"),
    ("¿Me puedes ayudar a cambiar la anterior?"),
    ("Que cubre una beca parcial?"),


])
def test_with_less_than_four_prior_interactions(handler, user_input):
    # Prepare history with two interactions: user, assistant
    initial_history = [{"role": "assistant", "content": "¿Qué tipo de financiamiento buscas? Opciones: parcial, completa, otros"},
        {"role": "user", "content": "parcial esta bien"},
        {"role": "assistant", "content": "Vale, entonces parcial, ahora ¿En qué área de estudios te interesan las becas? Opciones: ciencias_tecnicas, ciencias_sociales, arte_humanidades, salud, otros"},
        {"role": "user", "content": "relleno para que no falle el test"},
    ]
    ctx = HandlerContext(
        raw_text=user_input,
        normalized_text=user_input,
        history=initial_history.copy(),
        last_intention="buscar_por_criterio"
    )

    # Execute
    ctx = handler.handle(ctx)

    assert ctx.intention == "buscar_por_criterio"
