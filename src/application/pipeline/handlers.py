import re
from typing import Optional
from src.application.pipeline.interfaces import IHandler, HandlerContext
from src.domain.entities import DialogAct
from src.domain.interfaces import IntentClassifierService, ArgumentClassifierService
from src.infrastructure.intention_classifier import IntentionClassifier
from src.infrastructure.argument_classifier import ArgumentClassifier
from src.infrastructure.llm_response_builder import ResponseBuilder


class PreprocessHandler(IHandler):
    def __init__(self, next_handler: IHandler = None):
        self.next = next_handler

    def handle(self, ctx: HandlerContext) -> HandlerContext:
        # 1. Normalizar a minúsculas
        text = ctx.raw_text.lower()

        # 2. Quitar espacios redundantes
        text = re.sub(r'\s+', ' ', text).strip()

        # 3. Eliminar caracteres no deseados (solo dejamos letras, números y signos básicos)
        text = re.sub(r'[^a-z0-9áéíóúüñ¿¡?\s]', '', text)

        # 4. Guardar texto normalizado
        ctx.normalized_text = text

        # 5. Pasar al siguiente handler
        if self.next:
            return self.next.handle(ctx)
        return ctx
      
class HistoryHandler(IHandler):
    def __init__(self, next_handler: IHandler = None, max_history: int = 6):
        self.next = next_handler
        self.max_history = max_history

    def handle(self, ctx: HandlerContext) -> HandlerContext:
        # 1. Antes de procesar: añadir el mensaje del usuario al historial
        ctx.history.append({"role": "user", "content": ctx.normalized_text})

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
    
class CriteriaSearchHandler(IHandler):
    def __init__(
        self,
        classifier: ArgumentClassifierService = ArgumentClassifier(),
        next_handler: Optional[IHandler] = None,
        responder: "ResponseBuilder" = None,
    ):
        self.classifier = classifier
        self.next = next_handler
        self.responder = responder or ResponseBuilder()

    # ---------- 1) Punto de entrada ----------
    def handle(self, ctx: HandlerContext) -> HandlerContext:
        # if ctx.last_intention != "buscar_por_criterio":
        #     # Ni siquiera lo intento: paso al siguiente
        #     return self.next.handle(ctx) if self.next else ctx

        # ---- Intento clasificar dentro del flujo de criterios ----
        result = self.classifier.classify_with_test_promt(
            message=ctx.normalized_text,
            available_options=ctx.filter_criteria.active_fields,
            context=ctx.last_interaction()
        )

        if all(result.get(k) is not None for k in ("action", "field", "value")):
            # 1) Lista de actos
            acts: list[DialogAct] = []

            # a) Acto principal que devuelve filter_criteria.apply()
            act = ctx.filter_criteria.apply(result)      # puede ser None si no hubo cambio
            if act:
                acts.append(act)

            # b) Preguntar el siguiente campo, si lo hay
            if ctx.filter_criteria.has_pending_criteria():
                next_field = ctx.filter_criteria.next_pending_field()
                acts.append(DialogAct(type="ask_field", field=next_field))

            # 2) Enviamos siempre la misma estructura al builder
            ctx.response_message = self.responder.render(acts=acts, ctx=ctx)
            return ctx  


        return self.next.handle(ctx) if self.next else ctx

    
class IntentHandler(IHandler):
    def __init__(self, classifier: IntentClassifierService = IntentionClassifier(), next_handler: IHandler = None):
        self.classifier = classifier
        self.next = next_handler

    def handle(self, ctx: HandlerContext) -> HandlerContext:
        history_snippet = ctx.last_interaction          
            
        intent_result = self.classifier.classify_intention(message = ctx.normalized_text, context=history_snippet, last_intention=ctx.last_intention)
        ctx.intention = intent_result.get("intention")

        # 2. Pasar al siguiente handler
        if self.next:
            return self.next.handle(ctx)
        return ctx
    

    
class FlowHandler(IHandler): pass
class GenerationHandler(IHandler): pass
