import os
from typing import Any, Dict, List
from swiplserver import PrologMQI, PrologError
from domain.interfaces import ScholarshipRepository
from domain.entities import Scholarship

DEFAULT_KB_PATH = "config/becas.pl"

class PrologConnectorError(Exception):
    """Custom exception for Prolog connection or query errors."""
    pass

class NoResultsError(Exception):
    """Raised when a query returns no results."""
    pass

class PrologConnector(ScholarshipRepository):
    def __init__(self, kb_path: str = DEFAULT_KB_PATH):
        if not os.path.exists(kb_path):
            raise FileNotFoundError(f"KB not found at: {kb_path}")
        self.kb_path = kb_path
        
    def find_by_name(self, name: str) -> List[Scholarship]:
        # Busca todas las becas cuyo nombre coincida
        query = (
            f"findall(beca(Title,Desc,Fin,Reqs), "
            f"buscar_por_nombre('{name}',Title,Desc,Fin,Reqs),L)"
        )
        rows = self._run_query(query, ["L"])
        terms = rows[0]["L"]
        results = []
        for term in terms:
            args = term.get("args", [])
            results.append(Scholarship(
                code="",  # el código no está disponible en este predicado
                title=args[0],
                description=args[1],
                financing=args[2],
                requirements=args[3]
            ))
        return results
    
    def find_by_filters(self, criteria):
        raise NotImplementedError
    
    def list_all_names(self) -> List[str]:
        # Usamos findall para capturar todos los títulos
        query = "beca(Id)."
        results = self._run_query(query, ["Id"])
        names = [str(item['Id']) for item in results if 'Id' in item and isinstance(item['Id'], str)]
        return sorted(list(set(names)))     
    
    def _run_query(self, query: str, query_vars: List[str]) -> List[Dict[str, Any]]:
        try:
            with PrologMQI() as mqi:
                with mqi.create_thread() as prolog:
                    prolog.query(f"consult('{self.kb_path}')")

                    raw = prolog.query(query)
                    # Normalizar el retorno de raw:
                    if isinstance(raw, bool):
                        # False: no hay solución
                        if not raw:
                            raise NoResultsError(f"No results found for query: {query}")
                        # True: un hecho sin variables → ninguna binding que extraer
                        raw = []
                    else:
                        # Iterable de bindings
                        raw = list(raw)

                    if not raw:
                        raise NoResultsError(f"No results found for query: {query}")

                    filtered = []
                    for row in raw:
                        entry = {var: row[var] for var in query_vars if var in row}
                        if entry:
                            filtered.append(entry)

                    if not filtered:
                        raise NoResultsError(f"No results after filtering for query: {query}")
                    return filtered

        except PrologError as e:
            raise (f"Prolog error during query: {e}")
        except NoResultsError:
            raise
        except Exception as e:
            raise PrologConnectorError(f"Unexpected error during Prolog interaction: {e}")   
  

