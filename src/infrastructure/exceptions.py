
class JSONExtractionError(Exception):
    """Excepción para indicar que no se pudo extraer un JSON válido del texto."""
    pass

class IntentMismatchError(Exception):
    """Excepción para indicar que la intención del usuario no coincide con el flujo esperado."""
    pass


class PrologConnectorError(Exception):
    """Custom exception for Prolog connection or query errors."""
    pass

class NoResultsError(Exception):
    """Raised when a query returns no results."""
    pass
