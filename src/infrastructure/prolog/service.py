from pathlib import Path
from typing import Any, Dict, List
from swiplserver import PrologMQI, PrologError

from infrastructure.exceptions import NoResultsError, PrologConnectorError


DEFAULT_KB_PATH = "config/becas.pl"


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