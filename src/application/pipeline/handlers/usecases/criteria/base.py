import json
import logging
import pathlib
from abc import ABC, abstractmethod
from application.pipeline.context import HandlerContext


def load_config() -> dict:
    """Carga dinámicamente las plantillas de preguntas desde un fichero JSON."""
    logger = logging.getLogger(__name__)
    PROMPT_PATH = pathlib.Path("config/flow_config.json")
    
    try:
        with PROMPT_PATH.open(encoding="utf-8") as fh:
            templates = json.load(fh)
            logger.debug("Plantillas de preguntas cargadas: %s", list(templates.keys()))
            return templates
    except Exception as e:
        logger.error("Error cargando plantillas de preguntas desde %s: %s", PROMPT_PATH, e)
        return {}


CONFIG = load_config()
ASK_FIELDS = CONFIG.get("ask_field", {})


class AbstractCriteriaHandler(ABC):
    """
    Clase abstracta para handlers de criterios: implementa métodos comunes
    y deja abstractos los puntos de extensión necesarios.
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def handle(self, ctx: HandlerContext) -> HandlerContext:
        """Debe ser implementado por cada sub‐handler concreto."""
        pass

    @staticmethod
    def _pretty_format(option: str) -> str:
        """
        Formatea una opción individual: quita guiones bajos,
        capitaliza y resalta.
        """
        return f"<strong>{option.replace('_', ' ').capitalize()}</strong>"

    @staticmethod
    def _pretty_options(options: list[str]) -> str:
        """
        Formatea una lista de opciones como un string bonito.
        Elimina los guiones bajos y pone las primeras letras en mayúscula.
        """
        def fmt(opt: str) -> str:
          return opt.replace("_", " ").capitalize()
        n = len(options)

        if n == 0:
            return ""

        if n == 1:
            return f"Solo está esta opción: {fmt(options[0])}"

        # Varias opciones → unir con comas y «y» final
        pretties = [fmt(o) for o in options]
        cuerpo = ", ".join(pretties[:-1])
        return f"\nEstas son las opciones: {cuerpo} u {pretties[-1]}"
    def _build_and_set_response(self, ctx: HandlerContext, base_text: str) -> None:
        """
        Construye y asigna la respuesta para el siguiente campo pendiente,
        o confirma si no hay más campos.
        """
        next_field = ctx.criteria.next_pending()
        if next_field:
            display = self._pretty_format(next_field)
            cfg = ASK_FIELDS.get(next_field, {})
            question = cfg.get(
                "prompt",
                f"¿Cuál es el valor para {display}?"
            )
            options = self._pretty_options(cfg.get("options", []))
            ctx.response_message = f"{base_text}\n\n{question}\n{options}".strip()
            ctx.response_payload = {"text": ctx.response_message}
        else:
            sm = ctx.criteria_sm.collected_all()
            confirm_text = f"{base_text}¿Deseas confirmar estos criterios?\nPuedes modificar alguno si lo deseas."
            self.logger.debug("Criterios recogidos: %s", ctx.criteria_sm.get_state())
            selected = ctx.criteria.printable()
            ctx.response_message = f"{confirm_text}\n\n{selected}"
            ctx.response_payload = {"text": ctx.response_message}



