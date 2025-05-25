# application/pipeline/interfaces.py

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Protocol
from domain.entities import DialogAct, FilterCriteria

@dataclass
class IntentResultDTO:
    """
    Contenedor puro de datos para la salida del IntentHandler.
    Solo transporta la intención extraída del texto del usuario.
    """
    intention: Optional[str] = None
    
@dataclass
class BuscarPorCriterioDTO:
    active_fields: Optional[List[str]] = field(default_factory=list)
    area: Optional[str] = None
    organization: Optional[str] = None
    education_level: Optional[str] = None
    location: Optional[str] = None

    def to_domain(self) -> FilterCriteria:
        return FilterCriteria(

            area=self.area,
            education_level=self.education_level,
            location=self.location,
            organization=self.organization
        )
      
    def has_pending_criteria(self) -> bool:
        """
        Devuelve True si hay criterios pendientes de respuesta.
        """
        return any([
            self.area is None,
            self.education_level is None,
            self.location is None,
            self.organization is None
        ])
    def next_pending(self) -> Optional[str]:
        """
        Devuelve el siguiente criterio pendiente de respuesta.
        """
        if self.area is None:
            return "area"
        elif self.education_level is None:
            return "education_level"
        elif self.location is None:
            return "location"
        elif self.organization is None:
            return "organization"
        else:
            return None
    
    def update_last_answered_criterion(self, new_value: str):
        """
        Modifica el valor para el último criterio respondido.
        """
        if self.area is None:
            self.area = new_value
        elif self.education_level is None:
            self.education_level = new_value
        elif self.location is None:
            self.location = new_value
        elif self.organization is None:
            self.organization = new_value
        else:
            raise ValueError("No hay criterios pendientes de respuesta.")
    def apply(self, result: Dict[str, Any]):
        """
        Aplica los resultados de la clasificación a los campos correspondientes.
        """
        FIELD_MAP = {
            "campo_estudio": "area",
            "nivel": "education_level",
            "ubicacion": "location",
            "organismo": "organization"
        }
        action = result.get("action")
        field = result.get("field")
        value = result.get("value")
        
        parsed_field = FIELD_MAP.get(field)
        if action == "modify":
            old = getattr(self, parsed_field, None)
            setattr(self, parsed_field, value)
            return DialogAct("modify_field", field, old, value)
        if action == "select":
            setattr(self, parsed_field, value)
            return DialogAct("ack_field", field, None, value)    
        return        


@dataclass
class HandlerContext:
    raw_text: str
    normalized_text: str = None
    intention: Optional[str] = None
    last_intention: Optional[str] = None
    raw_intent_payload: Dict[str, Any] = field(default_factory=dict)
    filter_criteria: Optional[BuscarPorCriterioDTO] = None
    
    history: List[Dict[str, str]] = field(default_factory=list)
    # sugerencias que puede devolver el handler
    suggestions: List[str] = field(default_factory=list)
    response_payload: Any = None      # datos crudos (lista de becas, estructura de confirmación…)
    response_message: Optional[str] = None  # texto final para el usuario
    
    error: Optional[str] = None
    
    def last_interaction(self) -> str:
        """
        Devuelve un string con la última interacción completa:
        Asistente: …\nUsuario: …
        """
        if len(self.history) < 2:
            return ""
        # history almacena alternadamente user/assistant
        last_bot = self.history[-2]["content"]
        last_user = self.history[-1]["content"]
        return f"Asistente: {last_bot}\nUsuario: {last_user}"


class IHandler(Protocol):
    def handle(self, ctx: HandlerContext) -> HandlerContext:
      ...