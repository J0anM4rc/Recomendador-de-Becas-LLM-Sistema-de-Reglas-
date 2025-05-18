from abc import ABC, abstractmethod
from typing import List, Tuple
from domain.entities import Scholarship, FilterCriteria

class ScholarshipRepository(ABC):
    @abstractmethod
    def find_by_name(self, name: str) -> Scholarship: ...
    @abstractmethod
    def find_by_filters(self, criteria: FilterCriteria) -> List[Scholarship]: ...
    @abstractmethod
    def get_all_scholarship_names(self) -> List[str]: ...
    @abstractmethod
    def get_all_criteria(self, var) -> List[str]:
        ...


class IntentClassifierService(ABC):
    @abstractmethod
    def classify(self, text: str) -> dict: ...
    # @abstractmethod
    # def classify_all(self, text: str) -> dict: ...
    
class ArgumentClassifierService(ABC):
    @abstractmethod
    def classify_(self, text: dict) -> dict: ...
    
class LLMInterface(ABC):
    @abstractmethod
    def generate(self, prompt: str, history: List[Tuple[str, str]] = None) -> str: ...
