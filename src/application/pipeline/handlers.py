class Handler:
    def __init__(self, next=None): self.next = next
    def handle(self, ctx): 
        return self.next.handle(ctx) if self.next else {"response": "fallback"}

class PreprocessHandler(Handler): pass
class IntentHandler(Handler): pass
class FlowHandler(Handler): pass
class GenerationHandler(Handler): pass
