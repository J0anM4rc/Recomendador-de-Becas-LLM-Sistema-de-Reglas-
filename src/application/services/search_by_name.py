from typing import Dict, List
from difflib import get_close_matches
from src.domain.interfaces import ScholarshipRepository

class SearchByName:
    def __init__(self, repo: ScholarshipRepository):
        self.repo = repo

    def execute(self, name: str) -> Dict:
        # 1) Validación mínima
        if not name or len(name) < 3:
            return {"error": "Por favor indica al menos 3 caracteres del nombre."}

        # 2) Obtenemos lista de nombres canónicos
        try:
            all_names = self.repo.list_all_names()
        except Exception as e:
            return {"error": f"Error accediendo a la lista de becas: {e}"}

        # 3) Fuzzy‐match con difflib
        matches = get_close_matches(name, all_names, n=1, cutoff=0.7)
        if not matches:
            # Si no hay match, sugerimos posibles próximas opciones
            suggestions = get_close_matches(name, all_names, n=5, cutoff=0.4)
            msg = f"No encontré ninguna beca similar a '{name}'."
            if suggestions:
                msg += f" Quizá te refieras a: {', '.join(suggestions)}"
            return {"error": msg}

        # 4) Tomamos el match canónico
        canonical = matches[0]

        # 5) Ejecutamos la consulta real
        try:
            results = self.repo.find_by_name(canonical)
        except Exception as e:
            return {"error": str(e)}

        if not results:
            return {"error": f"No encontré la beca «{canonical}» pese a estar en la lista."}

        # 6) Formateamos la salida
        return {"scholarships": [
            {
                "title": b.title,
                "financing": b.financing,
                "description": b.description,
                "requirements": b.requirements
            } for b in results
        ]}
