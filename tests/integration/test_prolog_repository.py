# tests/test_integration_prolog_repository.py

import pytest
from infrastructure.prolog.connector import PrologService, PrologConnector


@pytest.fixture
def prolog_svc():
    prologService = PrologService(kb_path="config/becas.pl")
    svc = PrologConnector(service = prologService)
    yield svc
    prologService.close()

def test_list_financing_types_not_empty(prolog_svc):
    financing = prolog_svc._get_criteria("financiamiento")
    assert isinstance(financing, list)
    assert financing, "Se esperaba al menos un tipo de financiación desde Prolog"   

def test_list_organization_not_empty(prolog_svc):
    orgs = prolog_svc._get_criteria("organismo")
    assert isinstance(orgs, list)
    assert orgs, "Se esperaba al menos un organismo desde Prolog"

def test_list_location_not_empty(prolog_svc):
    location = prolog_svc._get_criteria("ubicacion")
    assert isinstance(location, list)
    assert location, "Se esperaba al menos un lugar desde Prolog"
    
def test_list_study_areas_not_empty(prolog_svc):
    study_areas = prolog_svc._get_criteria("campo_estudio")
    assert isinstance(study_areas, list)
    assert study_areas, "Se esperaba al menos un área de estudio desde Prolog"
    
def test_list_education_level_not_empty(prolog_svc):
    education_level = prolog_svc._get_criteria("nivel")
    assert isinstance(education_level, list)
    assert education_level, "Se esperaba al menos un área de estudio desde Prolog"

def test_get_all_criteria(prolog_svc):
    study_areas = prolog_svc.get_all_criteria(["campo_estudio", "financiamiento", "organismo"])
    assert isinstance(study_areas, list)
    assert all(isinstance(area, str) for area in study_areas), "Todos los valores de campo_estudio deben ser strings"
    
def test_get_all_scholarships_names(prolog_svc):
    scholarships = prolog_svc.get_all_scholarship_names()
    assert isinstance(scholarships, list)
    assert all(isinstance(scholarship, str) for scholarship in scholarships), "Todos los valores de beca deben ser strings"

