from ..protocols import IHandler
from application.pipeline.context import HandlerContext
from domain.ports import IntentExtractorService    

class IntentHandler(IHandler):
    """
    Llama al servicio de clasificación de intenciones y, 
    si no hay intención válida, la marca como 'otro'.
    Luego delega al RouterPostIntent.
    """
    def __init__(self, classifier: IntentExtractorService, fallback: IHandler):
        self.classifier = classifier
        self.fallback = fallback  # RouterPostIntent

    def handle(self, ctx: HandlerContext) -> HandlerContext:
        history_snippet = ctx.last_interaction()
        intent_result = self.classifier.classify_intention(
            message=ctx.normalized_text,
            context=history_snippet,
            intention=ctx.intention
        )
        intention = intent_result.get("intention")

        if intention in ctx.rejected_intentions:
            intention = "bucle"

        ctx.intention = intention
        return self.fallback.handle(ctx)