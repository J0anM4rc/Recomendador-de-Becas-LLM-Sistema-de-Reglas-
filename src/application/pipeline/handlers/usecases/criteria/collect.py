import logging
from infrastructure.exceptions import JSONExtractionError
from application.pipeline.context import HandlerContext
from .base import AbstractCriteriaHandler

class CollectCriteriaHandler(AbstractCriteriaHandler):
    def __init__(self, slot_extractor):
        super().__init__()
        self.slot_extractor = slot_extractor
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def handle(self, ctx: HandlerContext) -> HandlerContext:
        self.logger.debug("Manejando intención 'buscar_por_criterio' en estado 'collecting'")
        try:
            extraction = self.slot_extractor.extract_criterion(
                context=ctx.last_interaction()
            )
        except ValueError as e:
            self.logger.error("Error al clasificar la respuesta: %s", e)
            ctx.response_message = (
                "No he entendido que criterio quieres seleccionar.\n"
                "Por favor, escribe el nombre completo del campo y la opción que quieres seleccionar."
            )
            ctx.response_payload = {"text": ctx.response_message}
            return ctx
        except JSONExtractionError as e:
            self.logger.error("Error al extraer criterios: %s", e)
            ctx.response_message = (
                "El sistema no ha podido procesar tu solicitud correctamente.\n"
                "Por favor, intenta de nuevo con un mensaje más claro o específico."
                "Si el problema persiste, contacta con jmpereallodra@gmail.com."
            )
            ctx.response_payload = {"text": ctx.response_message}
            return ctx
        
        ctx.criteria.apply(extraction) 
        
        base_text = self._build_base_text(
            field=extraction.get("field"),
            value=extraction.get("value"),
        )
        self._build_and_set_response(ctx, base_text)
        return ctx

    def _build_base_text(self, field: str, value: str) -> str:
        """Construye el texto base para la respuesta, incluyendo el campo y valor seleccionados."""
        text = (
                f"Has seleccionado:\n"
                f"• {self._pretty_format(field)}: {self._pretty_format(value)}\n\n"
            )
        return text