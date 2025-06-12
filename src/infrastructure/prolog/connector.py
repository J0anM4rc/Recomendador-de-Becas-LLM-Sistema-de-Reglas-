from typing import List
from domain.ports import ScholarshipRepository
from infrastructure.exceptions import NoResultsError
from .service import PrologService


class PrologConnector(ScholarshipRepository):
    """
    Implementación de ScholarshipRepository usando PrologService.
    """
    def __init__(self, service: PrologService):
        self.service = service 
    def get_criteria(self, criterion) -> List[str]:
        rows = self.service.query(
            f"setof(Type, {criterion}(_,Type), Types)", ["Types"]
        )
        return sorted({str(row["Types"][0]) for row in rows })
    def get_all_criteria(self, criteria) -> List[str]:
        # Asume que en tu KB hay hechos área/1
        all_names = []
        for criterion in criteria:
            names = self.get_criteria(criterion)
            all_names.extend(names)
        return sorted(set(all_names))
            
    def find_by_filters(self, organization=None, area=None, financiamiento=None, education_level=None, location=None):
        """
        Busca becas según los filtros proporcionados.
        Params:
            organization (str): nombre del organismo.
            area (str): área de estudio.
            financiamiento (str): tipo de financiamiento.
            education_level (str): nivel educativo.
            location (str): ubicación geográfica.
        Returns:
            List[Dict[str, str]]: lista de becas encontradas con su nombre y descripción.
        """
        organization = organization or "_"
        area = area or "_"
        financiamiento = financiamiento or "_"
        education_level = education_level or "_"
        location = location or "_"
        
        # Construir la consulta Prolog
        query = (f"buscar_beca({organization}, {area}, {financiamiento}, "
             f"{education_level}, {location}, Beca, Info).")
        try:
            rows = self.service.query(query, ["Beca", "Info"])
        except NoResultsError:
            raise
        return [
            {"nombre": row["Beca"], "descripcion": row["Info"]}
            for row in rows
        ]
        
    def get_all_scholarship_names(self) -> List[str]:
        rows = self.service.query("setof(Name, beca(Name), Names)", ["Names"])
        return sorted(rows[0]["Names"])
    
    def get_requirements(self, scholarship_name: str) -> List[dict[str, str]]:
        """
        Obtiene los requisitos de una beca específica.

        Params:
            scholarship_name (str): nombre de la beca.

        Returns:
            List[dict[str, str]]: lista de requisitos con su nombre y descripción.
        """
        query = f"requisito({scholarship_name}, NombreRequisito, Descripcion)."
        
        rows = self.service.query(query, ["NombreRequisito", "Descripcion"])

        if not rows:
            return []

        return [
            {"nombre_requisito": row["NombreRequisito"], "descripcion": row["Descripcion"]}
            for row in rows
        ]
        
    def get_deadlines(self, scholarship_name: str) -> List[dict[str, str]]:
        """
        Obtiene los plazos de una beca específica.

        Params:
            scholarship_name (str): nombre de la beca.

        Returns:
            List[dict[str, str]]: lista de plazos con su nombre y fecha.
        """
        query = f"plazo({scholarship_name}, NombrePlazo, Fecha)."
        rows = self.service.query(query, ["NombrePlazo", "Fecha"])

        if not rows:
            return []

        return [
            {"nombre_plazo": row["NombrePlazo"], "fecha": row["Fecha"]}
            for row in rows
        ]