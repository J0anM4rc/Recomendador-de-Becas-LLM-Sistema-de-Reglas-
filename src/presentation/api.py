from fastapi import FastAPI, Depends
from src.application.pipeline.factory import build_pipeline

app = FastAPI()

def get_pipeline():
    return build_pipeline()

@app.post("/health")
def health(): return {"status": "ok"}

@app.post("/chat")
def chat(body: dict, pipeline = Depends(get_pipeline)):
    ctx = {"message": body.get("message","")}
    out = pipeline.handle(ctx)
    return {"response": out.get("response")}
