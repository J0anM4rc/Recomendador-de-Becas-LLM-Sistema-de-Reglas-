
from ..protocols import IHandler
from application.pipeline.context import HandlerContext

class RouterPostIntent(IHandler):
    """
    Tras IntentHandler, despacha según ctx.intention.
    """

    def __init__(self, criteria_handler: IHandler, requirements_handler: IHandler,
                 deadlines_handler: IHandler, general_handler: IHandler, fallback: IHandler ):
        self.criteria_handler = criteria_handler
        self.requirements_handler = requirements_handler
        self.deadlines_handler = deadlines_handler
        self.general_handler = general_handler
        self.fallback = fallback  

    def handle(self, ctx: HandlerContext) -> HandlerContext:
        intent = ctx.intention

        match intent:
            case "buscar_por_criterio":
                return self.criteria_handler.handle(ctx)
            case "requisitos_beca":
                return self.requirements_handler.handle(ctx)
            case "plazos_beca":
                return self.deadlines_handler.handle(ctx)
            case "general_qa":
                return self.general_handler.handle(ctx)
            case _:
                return self.fallback.handle(ctx)
