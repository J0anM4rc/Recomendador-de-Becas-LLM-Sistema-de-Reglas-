import pytest
from application.pipeline.general.handlers import PreprocessHandler
from pipeline.handlers.protocols import HandlerContext, IHandler

class DummyNextHandler(IHandler):
    def handle(self, ctx: HandlerContext) -> HandlerContext:
        ctx.response_payload = {"text": "dummy response"}
        return ctx

@pytest.fixture
def handler():
    return PreprocessHandler(next_handler=DummyNextHandler())

def test_text_is_lowercased(handler):
    ctx = HandlerContext(raw_text="Quiero UNA BECA")
    ctx = handler.handle(ctx)
    assert ctx.normalized_text == "quiero una beca"

def test_multiple_spaces_are_collapsed(handler):
    ctx = HandlerContext(raw_text="  Hola    mundo   ")
    ctx = handler.handle(ctx)
    assert ctx.normalized_text == "hola mundo"

def test_non_alphanumeric_characters_removed(handler):
    ctx = HandlerContext(raw_text="¿Becas!!! en *España*?")
    ctx = handler.handle(ctx)
    assert ctx.normalized_text == "¿becas en españa?"

def test_pipeline_continues_to_next(handler):
    ctx = HandlerContext(raw_text="Hola")
    ctx = handler.handle(ctx)
    assert ctx.response_payload["text"] == "dummy response"
