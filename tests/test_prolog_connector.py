import pytest
from app.prolog_connector import PrologConnector, PrologConnectorError, NoResultsError

@pytest.fixture(scope="module")
def connector():
    # Ajusta la ruta si tu estructura es distinta
    return PrologConnector(kb_path='becas.pl')

def test_buscar_beca_existe(connector):
    results = connector.buscar_beca('merito_academico', 'completa', 'pregrado', 'mexico')
    assert isinstance(results, list)
    assert any('Beca' in r and 'Info' in r for r in results)

def test_informacion_beca_existe(connector):
    results = connector.informacion_beca('beca_mexico_excelencia')
    assert isinstance(results, list)
    assert results[0]['Info'].startswith('Beca para estudiantes')

def test_explicacion_beca_existe(connector):
    results = connector.explicacion_beca('artistico')
    assert isinstance(results, list)
    assert results[0]['Explicacion'].startswith('Beca para personas')

def test_buscar_beca_no_resultado(connector):
    with pytest.raises(NoResultsError):
        connector.buscar_beca('necesidad_economica', 'completa', 'posgrado', 'europa')

def test_informacion_beca_no_resultado(connector):
    with pytest.raises(NoResultsError):
        connector.informacion_beca('beca_inexistente')

def test_explicacion_beca_no_resultado(connector):
    with pytest.raises(NoResultsError):
        connector.explicacion_beca('inexistente')

def test_consultas_prolog_error(monkeypatch):
    connector = PrologConnector(kb_path='becas.pl')
    # Simulamos un fallo genérico en la consulta
    def fake_query(_):
        raise Exception("error fake")
    monkeypatch.setattr(connector.prolog, 'query', fake_query)
    with pytest.raises(PrologConnectorError):
        connector.buscar_beca('merito_academico', 'completa', 'pregrado', 'mexico')
