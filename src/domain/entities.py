from dataclasses import dataclass
import random
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
    question: Optional[str]=None
    options: Optional[list]=None
    
    organization: Optional[str]=None
    area: Optional[str]=None
    education_level: Optional[str]=None
    location: Optional[str]=None
    def is_complete(self) -> bool:
        return all([self.area, self.organization, self.education_level, self.location])
    def random_incomplete_criterion(self) -> Optional[str]:
        fields = ['organization', 'area', 'education_level', 'location']
        missing = [f for f in fields if getattr(self, f) is None]
        return random.choice(missing) if missing else None

    def next_incomplete_criterion(self) -> Optional[str]:
        for field in ['organization', 'area', 'education_level', 'location']:
            if getattr(self, field) is None:
                return field
        return None
    def replace_cualquiera_with_none(self) -> None:
        for f in ['organization', 'area', 'education_level', 'location']:
            val = getattr(self, f)
            if isinstance(val, str) and val.strip().lower() == 'cualquiera':
                setattr(self, f, None)    
    
    

@dataclass
class DialogAct:
    type: str                    # p.e. "confirm_change", "ack_field", ...
    field: str | None = None
    old:   str | None = None
    new:   str | None = None