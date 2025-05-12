from src.infrastructure.llm_interface import DummyIntentClassifier
from src.infrastructure.prolog_scholarship_repository import PrologScholarshipRepository
from src.application.pipeline.handlers import PreprocessHandler, IntentHandler, FlowHandler, GenerationHandler

def build_pipeline():
    classifier = DummyIntentClassifier(None)
    repo = PrologScholarshipRepository(None)
    gen = GenerationHandler()
    flow = FlowHandler(next=gen)
    intent = IntentHandler(next=flow)
    pre = PreprocessHandler(next=intent)
    return pre
