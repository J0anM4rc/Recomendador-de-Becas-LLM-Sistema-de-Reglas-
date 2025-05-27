import re
from typing import Optional
from src.application.pipeline.interfaces import IHandler, HandlerContext
from src.domain.entities import DialogAct
from src.domain.interfaces import IntentClassifierService, ArgumentClassifierService
from src.infrastructure.intention_classifier import IntentionClassifier
from src.infrastructure.argument_classifier import ArgumentClassifier
from src.infrastructure.llm_response_builder import TemplateResponseBuilder


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
        basic_intention: IHandler = None, 
        prolog_query: IHandler = None, 
        responder : IHandler = None
    ):
        self.classifier = classifier
        self.basic_intention = basic_intention
        self.prolog_query = prolog_query
        self.responder = responder or TemplateResponseBuilder()
        

    # ---------- 1) Punto de entrada ----------
    def handle(self, ctx: HandlerContext) -> HandlerContext:
        if ctx.last_intention != "buscar_por_criterio":
            return self.next.handle(ctx) if self.next else ctx
        
        # Caso 1: El empieza la búsqueda por criterios
        elif not ctx.filter_criteria:
            # Si no hay criterios, inicializamos uno nuevo
            ctx.filter_criteria = ctx.filter_criteria.create_empty()
            result = self.classifier.extract_initial_criteria(
                context=ctx.last_interaction()
            )
            acts: list[DialogAct] = []
            acts.append(DialogAct(type="start_criteria_search", field=None, old=None, new=None))
            if all(result.get(k) is not None for k in ("action", "field", "value")):
                if act := ctx.filter_criteria.apply(result):
                    acts.append(act)
            if ctx.filter_criteria.has_pending_criteria():
                next_field = ctx.filter_criteria.next_pending()
                acts.append(DialogAct(type="ask_field", field=next_field))                
            return ctx
                    
        # Caso 2: El usuario ha respondido todos los criterios y se le pregunta si confirma la búsqueda
        elif ctx.filter_criteria and ctx.filter_criteria.is_complete():
            # Si ya hay criterios y están completos, no hacemos nada
            result = self.classifier.detect_confirmation(
                context=ctx.last_interaction()
            )
            acts: list[DialogAct] = []
            confirmation = result.get("confirmation")
            if confirmation == 'no':
                acts.append(DialogAct(type="reject_search", field=None, old=None, new=None))
                result = self.classifier.extract_initial_criteria(
                    context=ctx.last_interaction()
                )
                
                if all(result.get(k) is not None for k in ("action", "field", "value")):
                    if act := ctx.filter_criteria.apply(result):
                        acts.append(act)
            elif confirmation == "yes":
                acts.append(DialogAct(type="confirm_search", field=None, old=None, new=None))
                ctx.response_payload = ctx.filter_criteria.search()
                
            return ctx
            
        # Caso 3: El usuario ha respondido a un criterio pendiente    
        elif ctx.filter_criteria and ctx.filter_criteria.has_pending_criteria():
            result = self.classifier.classify_criterion_response(
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
                    next_field = ctx.filter_criteria.next_pending()
                    acts.append(DialogAct(type="ask_field", field=next_field))

                # 2) Enviamos siempre la misma estructura al builder
                ctx.response_message = self.responder.render(acts=acts, ctx=ctx)
                return ctx  

            ctx.rejected_intentions.append("buscar_por_criterio")
            return self.next.handle(ctx) if self.next else ctx

    
class IntentHandler(IHandler):
    def __init__(
        self, 
        classifier: IntentClassifierService = IntentionClassifier(), 
        search_by_criteria: IHandler = None, 
        scholarship_deadlines: IHandler = None, 
        scholarship_criteria: IHandler = None, 
        responder : IHandler = None
    ):
        self.classifier = classifier
        self.search_by_criteria = search_by_criteria
        self.scholarship_deadlines = scholarship_deadlines
        self.scholarship_criteria = scholarship_criteria
        self.responder = responder or TemplateResponseBuilder()

    def handle(self, ctx: HandlerContext) -> HandlerContext:
        history_snippet = ctx.last_interaction          
            
        intent_result = self.classifier.classify_intention(message = ctx.normalized_text, context=history_snippet, last_intention=ctx.last_intention)
        intention = intent_result.get("intention")
        
        if intention in ctx.rejected_intentions or not intention:
            intention = "general_qa"
            
        ctx.intention = intention
        match intention:
            case "buscar_por_criterio":
                return self.search_by_criteria.handle(ctx)
            case "plazos_beca":
                return self.scholarship_deadlines.handle(ctx)
            case "requisitos_beca":
                return self.scholarship_criteria.handle(ctx)            
            case _:
                return self.responder.handle(ctx)

    

    

class GenerationHandler(IHandler): pass
