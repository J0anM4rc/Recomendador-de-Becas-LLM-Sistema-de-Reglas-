from pathlib import Path
from typing import Any, Dict, List, Optional
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

class PrologService:
    """
    Servicio responsable de gestionar la conexión y ejecución de consultas Prolog.
    Carga la KB una sola vez al inicializarse y reutiliza el mismo contexto.
    """

    def __init__(self, kb_path: Path = DEFAULT_KB_PATH):
        # Asegurarse de trabajar con Path en todo momento
        self.kb_path = Path(kb_path)
        if not self.kb_path.exists():
            raise FileNotFoundError(f"KB not found at: {self.kb_path}")

        # Crear conexión a Prolog
        # self._mqi = PrologMQI()
        # self._thread = self._mqi.create_thread()

        # Cargar la KB una sola vez, usando rutas con barras '/'
        self.path_str = self.kb_path.resolve().as_posix()


    def query(self, goal: str, vars: List[str]) -> List[Dict[str, Any]]:
        """
        Ejecuta una consulta Prolog y devuelve los bindings solicitados.

        Params:
            goal (str): cadena del goal Prolog.
            vars (List[str]): lista de variables a extraer del resultado.
        Returns:
            lista de diccionarios {var: valor}.
        Raises:
            NoResultsError: si no hay resultados.
            PrologConnectorError: otros errores Prolog.
        """
        try:
            with PrologMQI() as mqi:
                with mqi.create_thread() as prolog:
                    prolog.query(f"consult('{self.path_str}')")
                    raw = prolog.query(goal)
                    if isinstance(raw, bool):
                        if not raw:
                            raise NoResultsError(f"No results for goal: {goal}")
                        raw = []
                    rows = list(raw)
                    if not rows:
                        raise NoResultsError(f"No results for goal: {goal}")
                    filtered = []
                    for row in rows:
                        entry = {v: row[v] for v in vars if v in row}
                        if entry:
                            filtered.append(entry)
                    if not filtered:
                        raise NoResultsError(f"No vars found in results for goal: {goal}")
                    return filtered
        except PrologError as e:
            raise PrologConnectorError(f"Prolog error: {e}") from e
        except NoResultsError:
            raise
        except Exception as e:
            raise PrologConnectorError(f"Unexpected error: {e}") from e
        
    def close(self):
        """
        Cierra el hilo de Prolog y destruye la instancia de PrologMQI para liberar recursos.
        """
        try:
            # Mata el hilo de Prolog que abrimos en __init__
            self._thread.stop()
        except Exception as e:
            # Aquí podrías loguear o ignorar según convenga
            raise PrologConnectorError(f"Error al cerrar el hilo de Prolog: {e}") from e

        try:
            # Destruye la instancia de MQI si existe ese método
            self._mqi.stop()
        except AttributeError:
            # Si no existe destroy(), quizá no sea necesario
            pass
        except Exception as e:
            raise PrologConnectorError(f"Error al destruir PrologMQI: {e}") from e



class PrologConnector(ScholarshipRepository):
    """
    Implementación de ScholarshipRepository usando PrologService.
    """
    def __init__(self, service: Optional[PrologService] = None, kb_path: Path = DEFAULT_KB_PATH):
        self.service = service or PrologService(kb_path)
    def get_criteria(self, criterion) -> List[str]:
        rows = self.service.query(
            f"setof(Type, {criterion}(_,Type), Types)", ["Types"]
        )
        return sorted({str(criterion["Types"][0]) for criterion in rows })
    def get_all_criteria(self, criteria) -> List[str]:
        # Asume que en tu KB hay hechos área/1
        all_names = []
        for criterion in criteria:
            names = self.get_criteria(criterion)
            all_names.extend(names)
        return sorted(set(all_names))
            
    def find_by_name(self, name: str) -> List[Scholarship]:
        raise NotImplementedError("find_by_name not implemented")
    def find_by_filters(self, criteria):
        raise NotImplementedError("find_by_filters not implemented")
    def get_all_scholarship_names(self) -> List[str]:
        rows = self.service.query("setof(Name, beca(Name), Names)", ["Names"])
        return sorted(rows[0]["Names"])
    


        
# class PrologConnector(ScholarshipRepository):
#     def __init__(self, kb_path: str = DEFAULT_KB_PATH):
#         if not os.path.exists(kb_path):
#             raise FileNotFoundError(f"KB not found at: {kb_path}")
#         self.kb_path = kb_path
        
#     def find_by_name(self, name: str) -> List[Scholarship]:
#         # Busca todas las becas cuyo nombre coincida
#         query = (
#             f"findall(beca(Title,Desc,Fin,Reqs), "
#             f"buscar_por_nombre('{name}',Title,Desc,Fin,Reqs),L)"
#         )
#         rows = self._run_query(query, ["L"])
#         terms = rows[0]["L"]
#         results = []
#         for term in terms:
#             args = term.get("args", [])
#             results.append(Scholarship(
#                 code="",  # el código no está disponible en este predicado
#                 title=args[0],
#                 description=args[1],
#                 financing=args[2],
#                 requirements=args[3]
#             ))
#         return results
    
#     def find_by_filters(self, criteria):
#         raise NotImplementedError
    
#     def list_all_names(self) -> List[str]:
#         # Usamos findall para capturar todos los títulos
#         query = "beca(Id)."
#         results = self._run_query(query, ["Id"])
#         names = [str(item['Id']) for item in results if 'Id' in item and isinstance(item['Id'], str)]
#         return sorted(list(set(names)))     
    
#     def list_study_areas(self) -> List[str]:
#         # Asume que en tu KB hay hechos área/1
#         query = "setof(Campo, beca_estudio(_, Campo), Campos)."
#         results = self.prolog._run_query(query, ["Campos"])
#         study_area = [str(item['Campos']) for item in results if 'Campos' in item and isinstance(item['X'], str)]
#         return sorted(list(set(study_area)))

#     def list_organization(self) -> List[str]:
#         results = self.prolog.query("organismo(X)")
#         return [r["X"] for r in results]

#     def list_financing_types(self) -> List[str]:
#         results = self.prolog.query("financiamiento(X)")
#         return [r["X"] for r in results]

#     def list_places(self) -> List[str]:
#         results = self.prolog.query("ubicacion(X)")
#         return [r["X"] for r in results]
    
#     def _run_query(self, query: str, query_vars: List[str]) -> List[Dict[str, Any]]:
#         try:
#             with PrologMQI() as mqi:
#                 with mqi.create_thread() as prolog:
#                     prolog.query(f"consult('{self.kb_path}')")

#                     raw = prolog.query(query)
#                     # Normalizar el retorno de raw:
#                     if isinstance(raw, bool):
#                         # False: no hay solución
#                         if not raw:
#                             raise NoResultsError(f"No results found for query: {query}")
#                         # True: un hecho sin variables → ninguna binding que extraer
#                         raw = []
#                     else:
#                         # Iterable de bindings
#                         raw = list(raw)

#                     if not raw:
#                         raise NoResultsError(f"No results found for query: {query}")

#                     filtered = []
#                     for row in raw:
#                         entry = {var: row[var] for var in query_vars if var in row}
#                         if entry:
#                             filtered.append(entry)

#                     if not filtered:
#                         raise NoResultsError(f"No results after filtering for query: {query}")
#                     return filtered

#         except PrologError as e:
#             raise (f"Prolog error during query: {e}")
#         except NoResultsError:
#             raise
#         except Exception as e:
#             raise PrologConnectorError(f"Unexpected error during Prolog interaction: {e}")   
  

