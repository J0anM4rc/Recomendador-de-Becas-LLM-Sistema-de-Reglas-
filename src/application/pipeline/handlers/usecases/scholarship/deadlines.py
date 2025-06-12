import logging
from typing import Any, List
from .base import BaseScholarshipHandler


class DeadlinesHandler(BaseScholarshipHandler):
    """
    Maneja la intención 'plazos_beca'
    """

    def __init__(self, scholarship_repository: Any, name_extractor: Any):
        super().__init__(scholarship_repository=scholarship_repository, name_extractor=name_extractor)
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def intent_name(self) -> str:
        """
        Nombre de la intención que maneja este handler.
        """
        return "plazos_beca"

    def fetch_data(self, arg)-> List[dict]:
        """
        Llama al método de Prolog para obtener los plazos de la beca indicada.
        """
        return self.scholarship_repository.get_deadlines(arg)

    @staticmethod
    def _no_results_text(scholarship_name: str) -> str:
        """
        Mensaje que se envía cuando Prolog no arroja resultados para la beca indicada.
        """
        return f"No encontré información sobre fechas para la beca «{BaseScholarshipHandler._pretty_option(scholarship_name)}»"
        
        
    def _build_scholarship_info_text(self, scholarship_name: str, items: List[dict]) -> str:
        """
        Construye un texto plano con la lista de plazos, uno por línea.
        """
        # Formatea el nombre de la beca para mostrarlo correctamente
        scholarship_name = BaseScholarshipHandler._pretty_option(scholarship_name)  
        if not items:
            # En caso de que Prolog devuelva lista vacía (aunque no lance NoResultsError)
            return f"No se encontraron los plazos para la beca «{scholarship_name}»."

        lines = [f" Plazo para la beca «{scholarship_name}»:"] 
        for req in items:
            # Formatea cada plazo
            name_deadline = BaseScholarshipHandler._pretty_option(req.get("nombre_plazo", ""))
            date_deadline = req.get("fecha", "")
            
            # Verifica que ambos campos existan
            if not name_deadline or not date_deadline:
                self.logger.warning(f"Plazo incompleto para la beca «{scholarship_name}»: {req}")
                continue
            # Agrega el plazo formateado a la lista
            lines.append(f"\n• {name_deadline}: {date_deadline}")
        return "\n".join(lines)
        