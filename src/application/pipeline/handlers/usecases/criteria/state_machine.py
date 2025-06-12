
from enum import Enum, auto

class CriteriaState(Enum):
    NOT_STARTED = auto()
    COLLECTING = auto()
    AWAITING_CONFIRMATION = auto()
    QUERYING = auto()
    COMPLETED = auto()

class CriteriaStateMachine:
    def __init__(self):
        self.state = CriteriaState.NOT_STARTED

    def reset(self):
        self.state = CriteriaState.NOT_STARTED

    def start(self):
        if self.state == CriteriaState.NOT_STARTED:
            self.state = CriteriaState.COLLECTING

    def collected_all(self):
        self.state = CriteriaState.AWAITING_CONFIRMATION

    def confirm_yes(self):
        if self.state == CriteriaState.AWAITING_CONFIRMATION:
            self.state = CriteriaState.QUERYING

    def confirm_no(self):
        if self.state == CriteriaState.AWAITING_CONFIRMATION:
            self.state = CriteriaState.COLLECTING

    def finish(self):
        if self.state == CriteriaState.QUERYING:
            self.state = CriteriaState.COMPLETED

    def is_not_started(self) -> bool:
        return self.state == CriteriaState.NOT_STARTED

    def is_collecting(self) -> bool:
        return self.state == CriteriaState.COLLECTING

    def is_awaiting_confirmation(self) -> bool:
        return self.state == CriteriaState.AWAITING_CONFIRMATION

    def is_querying(self) -> bool:
        return self.state == CriteriaState.QUERYING

    def is_completed(self) -> bool:
        return self.state == CriteriaState.COMPLETED

    def get_state(self) -> CriteriaState:
        return self.state
    def set_state(self, state: CriteriaState):
        if isinstance(state, CriteriaState):
            self.state = state
        else:
            raise ValueError("Invalid state type. Must be an instance of CriteriaState Enum.")