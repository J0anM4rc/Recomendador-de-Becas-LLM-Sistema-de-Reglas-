from domain.interfaces import IntentClassifierService
from domain.entities import FilterCriteria
class DummyIntentClassifier(IntentClassifierService):
    def __init__(self, model_path): ...
    def classify(self, text):
        return "fallback", FilterCriteria()
