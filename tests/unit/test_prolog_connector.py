import pytest
from pathlib import Path
from swiplserver import PrologError
from src.infrastructure.prolog_connector import PrologService, PrologConnectorError, NoResultsError

class DummyThread:
    def __init__(self, response):
        # response puede ser bool o iterable de dicts
        self._response = response

    def __enter__(self):
        class DummyProlog:
            def __init__(self, resp):
                self._resp = resp

            def query(self, goal):
                return self._resp

        return DummyProlog(self._response)

    def __exit__(self, exc_type, exc, tb):
        return False  # no silencia excepciones

class DummyMQI:
    def __init__(self, thread):
        self._thread = thread

    def create_thread(self):
        return self._thread

@pytest.fixture
def service(tmp_path, monkeypatch):
    # Crea un .pl vacío solo para evitar FileNotFoundError
    kb = tmp_path / "test.pl"
    kb.write_text("% empty\n")
    # Monta PrologService con MQI dummy
    dummy_thread = DummyThread(response=[])
    monkeypatch.setattr("src.infrastructure", lambda: DummyMQI(dummy_thread))
    return PrologService(kb_path=kb)

def test_query_success(monkeypatch, tmp_path):
    # Prepara un row de bindings
    kb = tmp_path / "test.pl"
    kb.write_text("% fichero de prueba vacío\n")
    
    row = {"X": "foo", "Y": 42}
    dummy_thread = DummyThread(response=[row])
    monkeypatch.setattr("src.infrastructure", lambda: DummyMQI(dummy_thread))
    svc = PrologService(kb_path=tmp_path / "test.pl")
    out = svc.query("some_goal", ["X", "Y"])
    assert out == [{"X": "foo", "Y": 42}]

def test_query_no_results_bool_false(monkeypatch, tmp_path):
    dummy_thread = DummyThread(response=False)
    monkeypatch.setattr("domain.services.PrologMQI", lambda: DummyMQI(dummy_thread))
    svc = PrologService(kb_path=tmp_path / "test.pl")
    with pytest.raises(NoResultsError):
        svc.query("nope", ["X"])

def test_query_raw_list_empty(monkeypatch, tmp_path):
    dummy_thread = DummyThread(response=[])
    monkeypatch.setattr("domain.services.PrologMQI", lambda: DummyMQI(dummy_thread))
    svc = PrologService(kb_path=tmp_path / "test.pl")
    with pytest.raises(NoResultsError):
        svc.query("empty", ["X"])

def test_query_prolog_error(monkeypatch, tmp_path):
    class BadThread(DummyThread):
        def __enter__(self):
            class BadProlog:
                def query(self, goal):
                    raise PrologError("boom")
            return BadProlog()
    monkeypatch.setattr("domain.services.PrologMQI", lambda: DummyMQI(BadThread(None)))
    svc = PrologService(kb_path=tmp_path / "test.pl")
    with pytest.raises(PrologConnectorError) as exc:
        svc.query("fail", ["X"])
    assert "Prolog error" in str(exc.value)
