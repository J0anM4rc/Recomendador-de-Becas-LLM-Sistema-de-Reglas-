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
    def create_empty() -> 'BuscarPorCriterioDTO':
        """
        Crea un DTO vacío con todos los campos a None.
        """
        return BuscarPorCriterioDTO(
            area=None,
            education_level=None,
            location=None,
            organization=None
        )
    def is_complete(self) -> bool:
        """
        Devuelve True si todos los criterios están definidos.
        """
        return all([
            self.area is not None,
            self.education_level is not None,
            self.location is not None,
            self.organization is not None
        ])
    def is_empty(self) -> bool:
        """
        Devuelve True si no hay criterios activos.
        """
        return not any([
            self.area,
            self.education_level,
            self.location,
            self.organization
        ])
      
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
    rejected_intentions: List[str] = field(default_factory=list)
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
        if len(self.history) == 0:
            return ""
        if len(self.history) < 2:
            # Si solo hay un mensaje, devolvemos solo el último
            return f"Usuario: {self.history[-1]['content']}"
        # history almacena alternadamente user/assistant
        last_bot = self.history[-2]["content"]
        last_user = self.history[-1]["content"]
        return f"Asistente: {last_bot}\nUsuario: {last_user}"


class IHandler(Protocol):
    def handle(self, ctx: HandlerContext) -> HandlerContext:
      ...