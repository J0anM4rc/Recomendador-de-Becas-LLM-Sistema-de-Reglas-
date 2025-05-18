class IHandler:
    def __init__(self, next=None): self.next = next
    def handle(self, ctx): 
        return self.next.handle(ctx) if self.next else {"response": "fallback"}

class PreprocessHandler(IHandler): pass
class IntentHandler(IHandler): pass
class ArgumentHandler(IHandler): pass
class FlowHandler(IHandler): pass
class GenerationHandler(IHandler): pass
