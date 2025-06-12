from abc import ABC, abstractmethod
from typing import List, Tuple


class ScholarshipRepository(ABC):
    @abstractmethod
    def find_by_filters(self, organization=None, area=None, financiamiento=None, education_level=None, location=None) -> List[dict]: ...
    @abstractmethod
    def get_all_scholarship_names(self) -> List[str]: ...
    @abstractmethod
    def get_all_criteria(self, var) -> List[str]:
        ...
        


class IntentExtractorService(ABC):
    @abstractmethod
    def extract(self, text: str) -> dict: ...

class SlotsExtractorService(ABC):
    @abstractmethod
    def extract(self, text: str) -> dict: ...
 
class LLMInterface(ABC):
    @abstractmethod
    def generate(self, prompt: str, history: List[Tuple[str, str]] = None) -> str: ...
