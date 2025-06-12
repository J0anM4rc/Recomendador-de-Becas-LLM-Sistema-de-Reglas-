
import logging
from .base import AbstractCriteriaHandler
from infrastructure.exceptions import JSONExtractionError
from application.pipeline.context import HandlerContext


class StartCriteriaHandler(AbstractCriteriaHandler):
    """
    Inicia el flujo de búsqueda por criterios:
      1) Arranca la máquina de estados y crea el DTO si hace falta.
      2) Extrae de una vez todos los criterios ya en el mensaje inicial.
      3) Pregunta por  el siguiente campo.
    """
    def __init__(self, slot_extractor):
        super().__init__()
        self.slot_extractor = slot_extractor
        self.logger = logging.getLogger(self.__class__.__name__)


    def handle(self, ctx: HandlerContext) -> HandlerContext:
        self.logger.debug("Manejando intención 'buscar_por_criterio' en estado 'starting'")
        # 1) Estado y DTO
        self._initialize(ctx)
        try:
            extraction = self.slot_extractor.extract_criterion(
                context=ctx.last_interaction(), 
                use_initial_prompt=True)
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
        self.logger.debug("Applied criterion %s=%s", extraction.get("field"), extraction.get("field"))
        
        base_text = self._build_base_text(extraction)        
        self._build_and_set_response(ctx, base_text)
        return ctx

    def _initialize(self, ctx: HandlerContext) -> None:
        sm = ctx.criteria_sm
        # Lazy init del DTO en ctx.arguments
        _ = ctx.criteria  
        # Arranca la máquina si es la primera vez
        if sm.is_not_started():
            sm.start()
            self.logger.debug("StateMachine: STARTED")   
            
    def _build_base_text(self, result: dict) -> str:
        text = (
            "Has iniciado una búsqueda de becas.\n"
            "Por favor, proporciona los criterios que deseas utilizar para filtrar las becas.\n\n"
        )
        field = result.get("field")
        value = result.get("value")
        if field and value:
            text += (
                f"He detectado como primer criterio:\n"
                f"• {AbstractCriteriaHandler._pretty_format(field)}: {AbstractCriteriaHandler._pretty_format(value)}\n\n"
            )
        return text


