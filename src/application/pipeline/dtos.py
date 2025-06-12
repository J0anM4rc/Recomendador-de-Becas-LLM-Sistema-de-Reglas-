from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Protocol

class FieldNotFoundError(Exception):
    """
    Excepción personalizada para indicar que un campo no fue encontrado en el DTO.
    Se usa para manejar errores de acceso a campos que no existen.
    """
    pass
        

@dataclass
class IntentResultDTO:
    """
    Contenedor puro de datos para la salida del IntentHandler.
    Solo transporta la intención extraída del texto del usuario.
    """
    intention: Optional[str] = None

@dataclass
class CriteriaDTO:
    active_fields: Optional[List[str]] = field(default_factory=list)
    area: Optional[str] = None
    organization: Optional[str] = None
    education_level: Optional[str] = None
    location: Optional[str] = None

    def create_empty() -> 'CriteriaDTO':
        """
        Crea una instancia vacía de CriteriaDTO.
        Inicializa todos los campos a None.
        """
        return CriteriaDTO(
            area=None,
            organization=None,
            education_level=None,
            location=None
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
      
    def printable(self) -> str:
        """
        Devuelve una representación en texto de los criterios activos.
        """
        criteria = []
        if self.area:
            criteria.append(f"Área: {self._pretty_option(self.area)}\n")
        if self.education_level:
            criteria.append(f"Nivel: {self._pretty_option(self.education_level)}\n")
        if self.location:
            criteria.append(f"Ubicación: {self._pretty_option(self.location)}\n")
        if self.organization:
            criteria.append(f"Organismo: {self._pretty_option(self.organization)}\n")
        
        return "\n".join(criteria) if criteria else "No hay criterios activos."
    def next_pending(self) -> Optional[str]:
        """
        Devuelve el siguiente criterio pendiente de respuesta.
        """
        if self.area is None:
            return "area"
        elif self.education_level is None:
            return "nivel"
        elif self.location is None:
            return "ubicacion"
        elif self.organization is None:
            return "organismo"
        else:
            return None
    
    def apply(self, result: Dict[str, Any]):
        """
        Aplica los resultados de la clasificación a los campos correspondientes.
        Retorna un diccionario con los campos actualizados.
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
        if not parsed_field:
            raise FieldNotFoundError(f"Campo no encontrado en el objeto Criteria: {field}")
        
        
        if action == "modify":
            old = getattr(self, parsed_field, None)
            setattr(self, parsed_field, value)
        elif action == "select":
            setattr(self, parsed_field, value)
        else:
            raise ValueError(f"Acción desconocida: {action} para el campo {field}")


    @staticmethod
    def _pretty_option(option: str) -> str:
        """
        Formatea una opción individual.
        Elimina los guiones bajos, pone las primeras letras en mayúscula y lo pone en negrita.
        """
        return f"<strong>{option.replace('_', ' ').capitalize()}</strong>"
    
    def get_criteria(self) -> dict:
        """
        Devuelve un diccionario con los criterios de búsqueda.
        """
        return {
            "area": self.area,
            "education_level": self.education_level,
            "location": self.location,
            "organization": self.organization
        }
