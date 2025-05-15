from abc import ABC, abstractmethod
from typing import List, Tuple
from domain.entities import Scholarship, FilterCriteria

class ScholarshipRepository(ABC):
    @abstractmethod
    def find_by_name(self, name: str) -> Scholarship: ...
    @abstractmethod
    def find_by_filters(self, criteria: FilterCriteria) -> List[Scholarship]: ...
    @abstractmethod
    def list_all_names(self) -> List[str]: ...

class IntentClassifierService(ABC):
    @abstractmethod
    def classify(self, text: str) -> Tuple[str, FilterCriteria]: ...
    @abstractmethod
    def classify_all(self, text: str) -> dict: ...
    
class LLMInterface(ABC):
    @abstractmethod
    def generate(self, prompt: str, history: List[Tuple[str, str]] = None) -> str: ...
