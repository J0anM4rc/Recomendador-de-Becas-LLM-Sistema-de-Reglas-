
from ..protocols import IHandler
from application.pipeline.context import HandlerContext

class RouterPostHistory(IHandler):
    """
    Si intention está en curso (p.ej. 'buscar_por_criterio') y no completado,
    envía directamente a ese handler. En otro caso, va a IntentHandler.
    """

    def __init__(self, criteria_handler: IHandler, requirements_handler: IHandler,
                 deadlines_handler: IHandler, intent_handler: IHandler):
        self.criteria_handler = criteria_handler
        self.requirements_handler = requirements_handler
        self.deadlines_handler = deadlines_handler
        self.intent_handler = intent_handler

    def handle(self, ctx: HandlerContext) -> HandlerContext:
        intent = ctx.intention

        if intent == "buscar_por_criterio" and not ctx.criteria_sm.is_completed():
            return self.criteria_handler.handle(ctx)

        if intent == "requisitos_beca":
            return self.requirements_handler.handle(ctx)

        if intent == "plazos_beca":
            return self.deadlines_handler.handle(ctx)
        

        # Si no estamos en ningún flujo activo, redirigimos a IntentHandler
        return self.intent_handler.handle(ctx)
