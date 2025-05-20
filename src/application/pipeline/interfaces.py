# application/pipeline/interfaces.py

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Protocol
from domain.entities import FilterCriteria

@dataclass
class IntentResultDTO:
    """
    Contenedor puro de datos para la salida del IntentHandler.
    Solo transporta la intención extraída del texto del usuario.
    """
    intention: Optional[str] = None
    
@dataclass
class BuscarPorCriterioDTO:
    question: Optional[str] = None
    options: Optional[List[str]] = None
    
    area: Optional[str] = None
    organization: Optional[str] = None
    education_level: Optional[str] = None
    location: Optional[str] = None

    def to_domain(self) -> FilterCriteria:
        return FilterCriteria(
            question=self.question,
            options=self.options,
            area=self.area,
            education_level=self.education_level,
            location=self.location,
            organization=self.organization
        )
      


@dataclass
class HandlerContext:
    raw_text: str
    normalized_text: str = None
    intention: Optional[str] = None
    last_intention: Optional[str] = None
    raw_intent_payload: Dict[str, Any] = field(default_factory=dict)

  
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