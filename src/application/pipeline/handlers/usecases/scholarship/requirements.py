from typing import Any, List
from .base import BaseScholarshipHandler
import logging

class RequirementsHandler(BaseScholarshipHandler):
    """
    Maneja la intención 'requisitos_beca'
    """

    def __init__(self, scholarship_repository: Any, name_extractor: Any):
        super().__init__(scholarship_repository = scholarship_repository, name_extractor = name_extractor)
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def intent_name(self) -> str:
        """
        Nombre de la intención que maneja este handler.
        """
        return "requisitos_beca"
    
    def fetch_data(self, arg: str) -> list[dict]:
        """
        Llama al método de Prolog para obtener los requisitos de la beca indicada.
        """
        return self.scholarship_repository.get_requirements(arg)
    
    
    @staticmethod
    def _no_results_text(scholarship_name: str) -> str:
        """
        Mensaje que se envía cuando Prolog no arroja resultados para la beca indicada.
        """
        return f"No encontré información requisitos para la beca «{BaseScholarshipHandler._pretty_option(scholarship_name)}»."
    
    
    def _build_scholarship_info_text(self, scholarship_name: str, items: List[dict]) -> str:
        """
        Construye un texto plano con la lista de requisitos, uno por línea.
        """
        # Formatea el nombre de la beca para mostrarlo correctamente
        scholarship_name = BaseScholarshipHandler._pretty_option(scholarship_name)  
        if not items:
            # En caso de que Prolog devuelva lista vacía (aunque no lance NoResultsError)
            return f"No se encontraron requisitos para la beca «{scholarship_name}»."

        lines = [f" Plazo para la beca «{scholarship_name}»:"] 
        for req in items:
            # Formatea cada plazo
            name_requirement = BaseScholarshipHandler._pretty_option(req.get("nombre_requisito"))
            description = req.get("descripcion")
            
            # Verifica que ambos campos existan
            if not name_requirement or not description:
                self.logger.warning(f"Requisito incompleto para la beca «{scholarship_name}»: {req}")
                continue
            # Agrega el plazo formateado a la lista
            lines.append(f"\n• {name_requirement}: {description}")
        return "\n".join(lines)