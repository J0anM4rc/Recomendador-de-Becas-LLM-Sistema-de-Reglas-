from src.application.pipeline.interfaces import IHandler, HandlerContext

    
class HistoryHandler(IHandler):
    def __init__(self, next_handler: IHandler = None, max_history: int = 6):
        self.next = next_handler
        self.max_history = max_history

    def handle(self, ctx: HandlerContext) -> HandlerContext:
        # 1. Antes de procesar: añadir el mensaje del usuario al historial
        ctx.history.append({"role": "user", "content": ctx.raw_text})

        # 2. Procesar siguiente handler
        if self.next:
            ctx = self.next.handle(ctx)

        # 3. Después de procesar: añadir la respuesta del asistente al historial
        bot_msg = ctx.response_payload.get("text")
        if bot_msg:
            ctx.history.append({"role": "assistant", "content": bot_msg})

        # 4. Truncar el historial a las últimas `max_history` entradas
        if len(ctx.history) > self.max_history:
            ctx.history = ctx.history[-self.max_history:]

        return ctx
class PreprocessHandler(IHandler): pass
class IntentHandler(IHandler): pass
class ArgumentHandler(IHandler): pass
class FlowHandler(IHandler): pass
class GenerationHandler(IHandler): pass
