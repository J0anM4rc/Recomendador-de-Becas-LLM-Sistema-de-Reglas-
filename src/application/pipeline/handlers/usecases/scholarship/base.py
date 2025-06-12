
import logging
from abc import ABC, abstractmethod
from typing import Any, List, Optional
from domain.ports import IntentExtractorService, ScholarshipRepository
from application.pipeline.handlers.protocols import IHandler
from application.pipeline.context import HandlerContext
from infrastructure.exceptions import NoResultsError

class BaseScholarshipHandler(IHandler, ABC):
    """
    Clase base para handlers de becas que:
    1) Extraen nombre de beca (o any arg) del contexto.
    2) Llaman a un método 'fetch_data' (ej. get_requirements, get_deadlines).
    3) Construyen un texto de respuesta con los datos obtenidos.
    4) Actualizan ctx y finalizan.
    """

    def __init__(self, scholarship_repository: ScholarshipRepository, name_extractor: IntentExtractorService):
        self.scholarship_repository = scholarship_repository
        self.name_extractor = name_extractor
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def handle(self, ctx: HandlerContext) -> HandlerContext:
        ctx.intention = self.intent_name()
        self.logger.debug(f"{self.__class__.__name__}: comenzando handle para intención '{ctx.intention}'")

        # 1) Extraer argumento (ej. nombre de beca) del contexto
        scholarship_name = self._extract_scholarship_name(ctx)
        if scholarship_name is None:
            ctx.response_payload = {"text": self._no_scholarship_error_text()}
            return ctx

        # 2) Intentar obtener datos de Prolog
        try:
            items = self.fetch_data(scholarship_name)
        except NoResultsError:
            ctx.response_payload = {"text": self._no_results_text(scholarship_name)}
            return ctx
        except Exception as e:
            self.logger.exception(f"Error inesperado al obtener datos para '{scholarship_name}': {e}")
            ctx.response_payload = {"text": "Lo siento, ha ocurrido un error al obtener la información de la beca."}
            return ctx


        # 3) Construir el texto de respuesta
        texto_info = self._build_scholarship_info_text(scholarship_name, items)

        # 4) Limpiar intención y guardar argumento para posibles iteraciones
        ctx.intention = None
        ctx.arguments["scholarship"] = scholarship_name
        
        # 5) Asignar el texto de respuesta directamente a response_payload
        ctx.response_payload = {"text": texto_info}
        self.logger.info(f"{self.__class__.__name__}: información de '{scholarship_name}' obtenida (n={len(items)})")
        
        return ctx

    def _extract_scholarship_name(self, ctx: HandlerContext) -> Optional[str]:
        """
        Intenta extraer el nombre de la beca:
        1) Primero, usando el name_extractor (NLU).
        2) Si no lo devuelve, toma ctx.arguments.get('scholarship') (consulta almacenada anteriormente).
        """
        self.logger.debug("Extrayendo nombre de la beca del contexto")
        result = self.name_extractor.extract_scholarship(context=ctx.last_interaction())
        argumento_nlu: Optional[str] = result.get("argumento")
        if argumento_nlu:
            self.logger.debug(f"Nombre de beca extraído por NLU: '{argumento_nlu}'")
            return argumento_nlu

        saved: Optional[str] = ctx.arguments.get("scholarship")
        if saved:
            self.logger.debug(f"Nombre de beca recuperado de ctx.arguments: '{saved}'")
        else:
            self.logger.debug("No se encontró nombre de beca en ctx.arguments")
        return saved
      
    @staticmethod
    def _no_scholarship_error_text() -> str:
        """
        Mensaje que se envía cuando no se pudo extraer ningún nombre de beca.
        """
        return (
            "Quiza no has mencionado una beca específica o no te he entendido bien.\n"
            "Si has mencionado el nombre de una beca, puede que no esté en mi base de datos.\n\n"
            "Para ayudarte mejor, puedes buscar becas filtrando por distintos criterios. "
            "Así podrás ver cuáles tengo registradas que se ajustan a tu perfil, "
            "y podré ofrecerte más información sobre ellas."
        )

    @staticmethod
    def _pretty_option(option: str) -> str:
        """
        Formatea una opción individual.
        Elimina los guiones bajos, pone las primeras letras en mayúscula y lo pone en negrita.
        """
        return f"<strong>{option.replace('_', ' ').capitalize()}</strong>"
      
    @abstractmethod
    def intent_name(self) -> str:
        """
        Nombre de la intención que maneja este handler. 
        Ejemplo: "requisitos_beca" o "plazos_beca".
        """
        pass

    @abstractmethod
    def fetch_data(self, arg: str) -> Any:
        """
        Llamada a Prolog:
        Ejemplo: prolog_query.get_requirements(arg) o get_deadlines(arg).
        Debe lanzar NoResultsError si no hay resultados.
        """
        pass

    @abstractmethod
    def _no_results_text(self, arg: str) -> str:
        """
        Mensaje de “no encontré resultados para ‘arg’”.
        """
        pass
      
    @abstractmethod 
    def _build_scholarship_info_text(self, scholarship_name: str, items: List[dict]) -> str:
        """
        Construye un texto plano con la información de la beca.
        """
        pass
        

      

