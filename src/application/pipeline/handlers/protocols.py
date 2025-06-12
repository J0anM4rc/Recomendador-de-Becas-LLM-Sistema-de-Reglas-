# application/pipeline/interfaces.py
from typing import  Protocol
from ..context import HandlerContext

class IHandler(Protocol):
    def handle(self, ctx: HandlerContext) -> HandlerContext:
      pass
      