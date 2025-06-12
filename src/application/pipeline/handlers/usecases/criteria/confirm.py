import logging
from typing import List
from infrastructure.exceptions import JSONExtractionError, NoResultsError
from application.pipeline.context import HandlerContext
from .base import AbstractCriteriaHandler


class ConfirmCriteriaHandler(AbstractCriteriaHandler):
    def __init__(self, slot_extractor, scholarship_repository):
        super().__init__()
        self.slot_extractor = slot_extractor 
        self.scholarship_repository =  scholarship_repository
        self.logger = logging.getLogger(self.__class__.__name__)

    def handle(self, ctx: HandlerContext) -> HandlerContext:
        self.logger.debug("Manejando intención 'buscar_por_criterio' en estado 'confirming'")
        sm = ctx.criteria_sm

        # 1) Detectar confirmación “sí/no”
        try:
            result = self.slot_extractor.extract_confirmation(
                context=ctx.last_interaction()
            )
            confirmation = result.get("confirmation")
        except ValueError as e:
            self.logger.error("Error detectando confirmación: %s", e)
            ctx.response_message = (
                "No he entendido tu respuesta. ¿Podrías decirme sí o no?"
            )
            ctx.response_payload = {"text": ctx.response_message}
            return ctx
        except JSONExtractionError as e:
            self.logger.error("Error al extraer criterios: %s", e)
            ctx.response_message = (
                "El sistema no ha podido procesar tu solicitud correctamente.\n"
                "Por favor, intenta de nuevo con un mensaje más claro."
                "Si el problema persiste, contacta con jmpereallodra@gmail.com."
            )
            ctx.response_payload = {"text": ctx.response_message}
            return ctx
        
        confirmation = result.get("confirmation")

        if confirmation == "yes":
            sm.confirm_yes()
            criteria = ctx.criteria.get_criteria()
            try:
                results = self.scholarship_repository.find_by_filters(**criteria)
            except NoResultsError as e:
                self.logger.error("No se encontraron resultados: %s", e)
                ctx.response_message = (
                    "No se encontraron becas que coincidan con los criterios seleccionados.\n"
                    "Puedes intentar modificando los criterios."
                )
                ctx.response_payload = {"text": ctx.response_message}
                ctx.intention = None
                sm.finish()
                return ctx
            
            ctx.response_message = self._build_scholarship_info_text(
                items=results
            )
            ctx.response_payload = {"text": ctx.response_message}
            ctx.intention = None
            sm.finish()
            return ctx
            
        elif confirmation == "no":
            try:
                mod_result = self.slot_extractor.extract_criterion(
                    context=ctx.last_interaction()
                )
            except ValueError as e:
                self.logger.error("Error al clasificar la respuesta: %s", e)
                ctx.response_message = (
                    "¿Qué criterio te gustaría modificar?.\n"
                )
                ctx.response_payload = {"text": ctx.response_message}
                sm.confirm_no()
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
            
            ctx.criteria.apply(mod_result) 
            base_text = self._build_base_text(
                field=mod_result.get("field"),
                value=mod_result.get("value")
            )
            self._build_and_set_response(ctx, base_text)
            return ctx

    def _build_scholarship_info_text(self, items: List[dict]) -> str:
        """
        Construye un texto plano con la lista de plazos, uno por línea.
        """
        if not items:
            # En caso de que Prolog devuelva lista vacía (aunque no lance NoResultsError)
            return f"No se encontró ninguna beca con esos criterios."

        lines = [f"He encontrado las siguientes becas:"] 
        for req in items:
            # Formatea cada plazo
            name = self._pretty_format(req["nombre"])
            description = req["descripcion"]
            # Agrega el plazo formateado a la lista
            lines.append(f"\n• {name}: {description}")
            
        lines.append("\nPuedes realizar una nueva búsqueda modificando los criterios.")
        return "\n".join(lines)
    

    def _build_base_text(self, field: str, value: str ) -> str:
        """Construye el texto base para la respuesta, incluyendo el campo y valor seleccionados."""
        text = (
                f"Has seleccionado:\n"
                f"• {self._pretty_format(field)}: {self._pretty_format(value)}\n\n"
            )
        return text