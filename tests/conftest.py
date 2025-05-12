# conftest.py
import logging
import pytest

class OnlyAppFilter(logging.Filter):
    def filter(self, record):
        # Solo dejar pasar logs cuyo logger empiece por "app."
        return record.name.startswith("app.")

def pytest_configure(config):
    # Añade el filtro a los handlers que usa pytest para el log_cli y la captura
    plugin = config.pluginmanager.get_plugin("logging-plugin")
    if plugin:
        for attr in ("log_cli_handler", "log_capture_handler"):
            handler = getattr(plugin, attr, None)
            if isinstance(handler, logging.Handler):
                handler.addFilter(OnlyAppFilter())

@pytest.fixture(autouse=True, scope="session")
def configure_logging():
    # Eliminamos handlers root por si quedan
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)

    # Creamos un handler único con nuestro filtro
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(levelname)s] %(name)s: %(message)s'))
    handler.addFilter(OnlyAppFilter())
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    # Silenciar otras librerías
    for lib in ("httpx", "httpcore", "urllib3", "requests", "swiplserver"):
        logging.getLogger(lib).setLevel(logging.WARNING)
    logging.getLogger("app.prolog_connector").setLevel(logging.INFO)
