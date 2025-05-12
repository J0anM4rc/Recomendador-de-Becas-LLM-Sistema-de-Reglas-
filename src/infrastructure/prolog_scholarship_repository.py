from domain.interfaces import ScholarshipRepository
from domain.entities import Scholarship
class PrologScholarshipRepository(ScholarshipRepository):
    def __init__(self, kb_path): ...
    def find_by_code(self, code):
        raise NotImplementedError
    def find_by_filters(self, criteria):
        raise NotImplementedError
