from ..protocols import IHandler
from application.pipeline.context import HandlerContext


class FallbackHandler(IHandler):
    """
    Handler de reserva para mensajes que no se entienden. 
    Informa al usuario que no se ha podido entender y recuerda que eres un asistente de becas.
    """

    def handle(self, ctx: HandlerContext) -> HandlerContext:
        texto = (
            "Lo siento, no he entendido tu mensaje. "
            "Soy un asistente de becas y puedo ayudarte con información sobre convocatorias, "
            "requisitos, plazos y búsqueda de becas. "
            "Si detectas algún error o quieres intentar de nuevo, por favor reformula tu pregunta."
        )
        ctx.response_message = texto
        ctx.response_payload = {"text": texto}
        ctx.history.append({"role": "assistant", "content": texto})

        return ctx
