from app.prolog_connector import PrologConnector
import pytest
from unittest.mock import MagicMock
from app.intention_classifier import IntentionClassifier

# This global classifier will be used for integration tests
# Ensure becas.pl is in the correct path relative to where pytest is run
# or provide an absolute path.
try:
    prolog_conn = PrologConnector(kb_path="becas.pl") # Adjust if your file is elsewhere
    classifier = IntentionClassifier(prolog_connector=prolog_conn)
except Exception as e:
    pytest.fail(f"Failed to initialize PrologConnector for integration tests: {e}")


@pytest.fixture
def classifier_with_mock():
    # This fixture is for unit tests, not integration tests
    mock_prolog_connector = MagicMock(spec=PrologConnector)
    # Simulate a successful load of some scholarship IDs
    mock_prolog_connector._run_query.return_value = [{'Id': 'beca_mec_general'}, {'Id': 'beca_santander_idiomas'}]

    classifier_mocked = IntentionClassifier(prolog_connector=mock_prolog_connector)
    classifier_mocked.llm.generate = MagicMock()
    # Overwrite with specific values for consistent mock testing
    classifier_mocked.posibles_becas_ids = ["beca_mec_general", "beca_santander_idiomas"]
    classifier_mocked.posibles_tipos = ["merito_academico", "situacion_economica", "completa", "parcial"]
    return classifier_mocked

# --- Existing Unit Tests (ensure they use classifier_with_mock) ---
def test_classify_intent_guiado(classifier_with_mock):
    classifier_with_mock.llm.generate.return_value = '{"intencion": "guiado"}'
    assert classifier_with_mock.classify_intent("ayúdame a buscar") == "guiado"

def test_classify_intent_invalid_json(classifier_with_mock):
    classifier_with_mock.llm.generate.return_value = 'respuesta inválida'
    assert classifier_with_mock.classify_intent("mensaje raro") == "general_qa"

def test_extract_beca_argument_single(classifier_with_mock):
    classifier_with_mock.llm.generate.return_value = '{"argumento": ["beca_mec_general"]}'
    result = classifier_with_mock.extract_beca_argument("Quiero info sobre beca mec")
    assert result == ["beca_mec_general"]

def test_extract_beca_argument_none(classifier_with_mock):
    classifier_with_mock.llm.generate.return_value = '{"argumento": null}'
    result = classifier_with_mock.extract_beca_argument("Hola, ¿cómo estás?")
    assert result is None

def test_extract_type_argument_multiple(classifier_with_mock):
    # Ensure fixture has these types
    classifier_with_mock.posibles_tipos = ["merito_academico", "situacion_economica"]
    classifier_with_mock.llm.generate.return_value = '{"argumento": ["merito_academico", "situacion_economica"]}'
    result = classifier_with_mock.extract_type_argument(
        "Tengo buen expediente y pocos recursos"
    )
    assert result == ["merito_academico", "situacion_economica"]


@pytest.mark.parametrize("user_input, llm_response, expected", [
    ("ayúdame a buscar", '{"intencion": "guiado"}', "guiado"),
    ("¿Qué sabes de beca_mec_general?", '{"intencion": "info_beca"}', "info_beca"),
    ("¿Qué es mérito académico?", '{"intencion": "explicacion_tipo"}', "explicacion_tipo"),
    ("Hola", '{"intencion": "chit_chat"}', "chit_chat"),
    ("¿Qué documentos suelen pedir?", '{"intencion": "general_qa"}', "general_qa"),
    ("sí", '{"intencion": "navegacion_flujo"}', "navegacion_flujo"),
    ("mensaje raro", 'respuesta sin JSON', "general_qa"),  # inválido
])
def test_classify_intent_parametrized(classifier_with_mock, user_input, llm_response, expected):
    classifier_with_mock.llm.generate.return_value = llm_response
    assert classifier_with_mock.classify_intent(user_input) == expected

def test_classify_full_method(classifier_with_mock):
    classifier_with_mock.llm.generate.return_value = '{"intencion": "chit_chat"}'
    result = classifier_with_mock.classify("Hola")
    assert result == {"intencion": "chit_chat", "argumento": None}

# --- Existing Integration Tests (ensure they use the global `classifier`) ---
@pytest.mark.integration
def test_real_classify_intent():
    intent = classifier.classify_intent("Hola")
    # LLM might interpret simple greetings differently, general_qa is also plausible sometimes
    assert intent in {"chit_chat", "general_qa", "navegacion_flujo"}

@pytest.mark.integration
def test_real_extract_beca_argument():
    result = classifier.extract_beca_argument("Quiero info sobre la beca excelencia mexico")
    # Assuming 'beca_mexico_excelencia' is a valid ID loaded from becas.pl
    assert "beca_mexico_excelencia" in result if result else False

@pytest.mark.integration
def test_real_extract_type_argument():
    # The global classifier's `posibles_tipos` will be used.
    # It's initialized with a default list if Prolog doesn't provide specific types.
    # We expect "merito_academico" to be in that default list or loaded.
    result = classifier.extract_type_argument("Tengo mérito académico")
    assert "merito_academico" in result if result else False

@pytest.mark.integration
def test_real_classify_complete():
    result = classifier.classify("Explícame qué es mérito académico")
    assert result["intencion"] in {"explicacion_tipo", "general_qa"}
    if result["intencion"] == "explicacion_tipo":
        assert "merito_academico" in result["argumento"] if result["argumento"] else False


# --- NEW Integration Tests for Enhanced NLU ---

@pytest.mark.integration
@pytest.mark.parametrize("user_input, expected_intent_options", [
    ("Quiero encontrar una beca para estudiar Ingenieria Informatica el año que viene.", {"guiado"}),
    ("Estoy interesado en optar a una beca universitaria, ¿me ayudas a buscar opciones?", {"guiado"}),
    ("Busco ayudas económicas para estudiar un máster", {"guiado"}),
    ("Necesito apoyo financiero para mis estudios", {"guiado"}),
    ("¿Me podrías recomendar becas internacionales para postgrado?", {"guiado"}),
    ("Quiero explorar becas de movilidad Erasmus, ¿me guías?", {"guiado"}),
    ("Estoy buscando becas para estudiantes de ciencias, ¿qué programas existen?", {"guiado"}),
    ("¿Cómo puedo encontrar becas para investigación en biología?", {"guiado"}),
    ("Me gustaría recibir información sobre becas para estudios de arte, ¿me ayudas a buscarlas?", {"guiado"}),
    ("Deseo acceder a becas de tecnología, ¿puedes ayudarme a buscar algunas?", {"guiado"}),
    ("¿Podrías ayudarme a filtrar becas según mi perfil académico?", {"guiado"}),
    ("Necesito encontrar becas para estudiantes con necesidad económica, ¿me orientas?", {"guiado"}),
    ("Voy a empezar un FP superior, ¿puedo optar a alguna beca?", {"guiado"}),
    ("Este año me gustaría solicitar alguna beca.", {"guiado"}),
])
def test_real_classify_intent_nuanced(user_input, expected_intent_options):
    """Tests intent classification with more varied and nuanced language."""
    intent = classifier.classify_intent(user_input)
    assert intent in expected_intent_options, f"Input: '{user_input}', Got: '{intent}', Expected one of: {expected_intent_options}"

@pytest.mark.integration
@pytest.mark.parametrize("user_input, expected_beca_ids", [
    ("Háblame de la beca del MEC.", ["beca_mec_general"]),
    ("Me interesa la beca CONACYT Nacional y también la Eiffel.", ["beca_conacyt_nacional", "beca_eiffel_excelencia"]),
    ("¿Qué sabes sobre la beca de La Caixa para posgrados?", ["beca_la_caixa_posgrado"]),
    ("No quiero la beca de transporte de la GV, sino la de excelencia de allí.", ["beca_gv_excelencia"]), # Negation + specific
    ("Busco info de la beca de Santander para aprender inglés.", ["beca_santander_idiomas"]),
    ("¿La beca de excelencia de la Generalitat Valenciana sigue abierta?", ["beca_gv_excelencia"]),
    ("¿Qué onda con la beca OEA?", ["beca_oea_desarrollo"]), # Colloquial
])
def test_real_extract_beca_argument_complex(user_input, expected_beca_ids):
    """Tests beca argument extraction with partial names, multiple mentions, and context."""
    result = classifier.extract_beca_argument(user_input)
    assert result is not None, f"Expected beca IDs for '{user_input}', got None"
    assert all(beca_id in result for beca_id in expected_beca_ids), \
           f"Input: '{user_input}', Got: {result}, Expected to contain: {expected_beca_ids}"
    # Optionally, for stricter tests if only specific IDs are expected:
    assert len(result) == len(expected_beca_ids), \
           f"Input: '{user_input}', Got: {result} (len {len(result)}), Expected exactly: {expected_beca_ids} (len {len(expected_beca_ids)})"


# @pytest.mark.integration
# @pytest.mark.parametrize("user_input, expected_types", [
#     ("Necesito ayuda económica, ¿qué becas hay para eso?", ["necesidad_economica"]),
#     ("¿Hay becas que cubran todo? Y también me interesan las que son por buen rendimiento académico.", ["completa", "merito_academico"]),
#     ("No me interesan las becas deportivas, prefiero las que son por mis notas.", ["merito_academico"]), # Negation + preference
#     ("¿Qué significa 'financiación parcial'?", ["parcial"]),
#     ("Busco una beca por mis logros deportivos y que me pague la matrícula.", ["deportivo", "matricula"]),
# ])
# def test_real_extract_type_argument_complex(user_input, expected_types):
#     """Tests type argument extraction with synonyms, multiple mentions, and context."""
#     # Ensure the classifier's posibles_tipos includes the expected ones for this test
#     # (it should from the default or Prolog loading)
#     result = classifier.extract_type_argument(user_input)
#     assert result is not None, f"Expected types for '{user_input}', got None"
#     assert all(t in result for t in expected_types), \
#            f"Input: '{user_input}', Got: {result}, Expected to contain: {expected_types}"
#     assert len(result) == len(expected_types), \
#            f"Input: '{user_input}', Got: {result} (len {len(result)}), Expected exactly: {expected_types} (len {len(expected_types)})"


# @pytest.mark.integration
# @pytest.mark.parametrize("user_input, expected_intent, expected_argument_subset", [
#     (
#         "Quiero saber más de la beca del MEC, especialmente si cubre la matrícula y es para gente con pocos recursos.",
#         "info_beca", # Primary intent is about the MEC beca
#         ["beca_mec_general"] # Argument extraction for info_beca focuses on beca_id
#     ),
#     (
#         "No entiendo la diferencia entre una beca completa y una parcial, ¿cuál me conviene más?",
#         "explicacion_tipo",
#         ["completa", "parcial"]
#     ),
#     (
#         "Estoy buscando becas para posgrado en Francia, he oído hablar de la Eiffel. ¿Esa es por mérito académico?",
#         "info_beca", # More specific than general_qa due to "Eiffel"
#         ["beca_eiffel_excelencia"]
#         # Although "mérito académico" is mentioned, the primary intent is info on Eiffel.
#         # The current `classify` logic only extracts one type of argument based on intent.
#     ),
#     (
#         "Si tengo buenas notas y mi familia no tiene mucho dinero, ¿qué becas como la MEC podría solicitar?",
#         "general_qa", # This is a more general query, not directly asking *about* "beca_mec_general" itself.
#                       # Or it could be info_beca if the LLM strongly associates "como la MEC" with MEC.
#                       # If it were info_beca, argument would be ["beca_mec_general"]
#         None # For general_qa, argument is None. If intent becomes info_beca, this should be ["beca_mec_general"]
#     ),
# ])
# def test_real_classify_complete_complex_queries(user_input, expected_intent, expected_argument_subset):
#     """Tests the full classify method with complex user queries."""
#     result = classifier.classify(user_input)

#     # Allow for flexibility if general_qa is an alternative for the last case
#     if user_input.startswith("Si tengo buenas notas") and result["intencion"] == "info_beca":
#         assert result["intencion"] == "info_beca"
#         assert "beca_mec_general" in result["argumento"] if result["argumento"] else False
#     else:
#         assert result["intencion"] == expected_intent, f"Input: '{user_input}'"

#     if expected_argument_subset:
#         assert result["argumento"] is not None, f"Expected argument for '{user_input}', got None"
#         assert all(arg_item in result["argumento"] for arg_item in expected_argument_subset), \
#                f"Input: '{user_input}', Got args: {result['argumento']}, Expected subset: {expected_argument_subset}"
#     else:
#         assert result["argumento"] is None, f"Expected no argument for '{user_input}', got {result['argumento']}"