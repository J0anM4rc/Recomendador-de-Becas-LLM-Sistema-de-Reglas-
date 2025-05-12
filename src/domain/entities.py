from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class Scholarship:
    code: str
    title: str
    financing: str
    requirements: Dict[str,str]
    def is_full_financing(self) -> bool:
        return self.financing.lower() in ("completa","total")

@dataclass
class FilterCriteria:
    organisation: Optional[str]=None
    area: Optional[str]=None
    financing: Optional[str]=None
    education_level: Optional[str]=None
    place: Optional[str]=None
    def is_complete(self) -> bool:
        return all([self.area, self.financing, self.place])
