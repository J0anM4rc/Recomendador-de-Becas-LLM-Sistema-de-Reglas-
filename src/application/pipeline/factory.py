# src/application/pipeline/factory.py

from src.infrastructure.llm_interface import LLAMAInterface
from src.infrastructure.prolog_connector import PrologConnector
from src.intention_classifier import IntentionClassifier
from src.logic_manager import LogicManager
from src.application.pipeline.handlers import (
    PreprocessHandler,
    IntentHandler,
    FlowHandler,
    GenerationHandler,
)
from src.application.services.search_by_name import SearchByName

def build_pipeline(model_path: str, kb_path: str):
    # 1) Adaptadores
    llm = LLAMAInterface(model_path)
    prolog = PrologConnector(kb_path)

    # 2) NLU y lógica
    classifier = IntentionClassifier(llm)
    logic = LogicManager(prolog)

    # 3) Mapeo intención → Use Case
    intent_map = {
        "buscar_beca_por_nombre": SearchByName,
        # aquí puedes añadir más intenciones y sus casos de uso
    }

    # 4) Construcción de la cadena de handlers
    gen        = GenerationHandler(llm)
    flow       = FlowHandler(logic, intent_map, next_handler=gen)
    intent     = IntentHandler(classifier, next_handler=flow)
    preprocess = PreprocessHandler(next_handler=intent)

    return preprocess
