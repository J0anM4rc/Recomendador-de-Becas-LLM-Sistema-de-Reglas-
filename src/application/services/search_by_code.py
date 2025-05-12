from domain.interfaces import ScholarshipRepository
class SearchByCode:
    def __init__(self, repo: ScholarshipRepository):
        self.repo = repo
    def execute(self, code: str):
        return {"error":"no implementado aún"}
