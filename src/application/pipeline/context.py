
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from .dtos import CriteriaDTO


@dataclass
class HandlerContext:
    raw_text: str
    normalized_text: str = ""
    response_message: str = ""
    response_payload: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, str]] = field(default_factory=list)

    intention: Optional[str] = None
    rejected_intentions: List[str] = field(default_factory=list)

    _state_machines: Dict[str, Any] = field(default_factory=dict)

    arguments: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    error: Optional[str] = None
    
    @property
    def criteria(self) -> CriteriaDTO:
        """
        Devuelve el DTO de criterios, inicializándolo en arguments si no existía.
        """
        dto = self.arguments.get("criteria")
        if dto is None:
            dto = CriteriaDTO.create_empty()
            self.arguments["criteria"] = dto
        return dto
      
    @property
    def criteria_sm(self) :
        """
        Devuelve el state machine de criterios, inicializándolo en _state_machines si no existía.
        """
        sm = self._state_machines.get("criteria_sm")
        if sm is None:
            from application.pipeline.handlers.usecases.criteria import CriteriaStateMachine
            sm = CriteriaStateMachine()
            self._state_machines["criteria_sm"] = sm
        return sm
    
    def last_interaction(self) -> str:
        """
        Devuelve un string con la última interacción completa:
        Asistente: …\nUsuario: …
        """
        print(self.history)
        if len(self.history) == 0:
            return ""
        if len(self.history) < 2:
            # Si solo hay un mensaje, devolvemos solo el último
            return f"Usuario: {self.history[-1]['content']}"
        # history almacena alternadamente user/assistant
        last_bot = self.history[-2]["content"]
        last_user = self.history[-1]["content"]
        return f"Asistente: {last_bot}\nUsuario: {last_user}"
