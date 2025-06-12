from application.pipeline.context import HandlerContext
from application.pipeline.handlers.protocols import IHandler
from infrastructure.exceptions import IntentMismatchError
from ...general.intent import IntentHandler
import logging
from . import (
    start,
    collect,
    confirm
)

logger = logging.getLogger(__name__)
class CriteriaHandler(IHandler):
    """
    Contenedor que despacha al sub‐handler apropiado según el estado de ctx.criteria_sm.
    """

    def __init__(
        self,
        start_handler: start.StartCriteriaHandler,
        collect_handler: collect.CollectCriteriaHandler,
        confirm_handler: confirm.ConfirmCriteriaHandler,
        intent_handler: IntentHandler

    ):
        self.start_handler = start_handler
        self.collect_handler = collect_handler
        self.confirm_handler = confirm_handler
        self.intent_handler = intent_handler


    def handle(self, ctx: HandlerContext) -> HandlerContext:
        sm = ctx.criteria_sm        
        ctx.intention = "buscar_por_criterio"
        
        logger.debug("Manejando intención 'buscar_por_criterio' con estado: %s", sm.state)
        try:
            if sm.is_not_started():
                return self.start_handler.handle(ctx)

            if sm.is_collecting() or sm.is_completed():
                return self.collect_handler.handle(ctx)

            if sm.is_awaiting_confirmation():
                return self.confirm_handler.handle(ctx)
        except IntentMismatchError as e:
            logger.error("Error en el manejo de criterios: %s", e)
            return self.intent_handler.handle(ctx)

        # Si el estado es COMPLETED o inválido, rechazamos
        ctx.rejected_intentions.append("buscar_por_criterio")
        return ctx
