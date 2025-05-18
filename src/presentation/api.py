from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Optional

from application.pipeline.factory import build_pipeline
from application.pipeline.interfaces import HandlerContext

# Inicialización de FastAPI y construcción de la pipeline
app = FastAPI()
# Aquí debes proporcionar las dependencias reales de tu aplicación:
# llm_client, criteria_repo, scholarship_repo, fuzzy_matcher, etc.
pipeline = build_pipeline(
    llm_client=...,          # Cliente LLM (p.ej. instancia de LLAMAInterface)
    criteria_repo=...,       # Implementación de CriteriaRepository (PrologCriteriaRepository)
    scholarship_repo=...,    # Implementación de ScholarshipRepository (PrologScholarshipRepository)
    fuzzy_matcher=...        # Implementación de FuzzyMatcher
)

# Modelos de datos para request y response
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    response: str
    history: List[Dict[str, str]]

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """
    Endpoint para procesar mensajes de chat.
    - Recibe el mensaje del usuario y un historial opcional.
    - Ejecuta la pipeline de handlers.
    - Devuelve la respuesta generada y el historial completo actualizado.
    """
    # 1. Crear contexto con mensaje y historial previo
    ctx = HandlerContext(
        raw_text=req.message,
        history=req.history or []
    )
    # 2. Procesar pipeline
    ctx = pipeline.handle(ctx)
    # 3. Devolver respuesta y nuevo historial
    return ChatResponse(
        response=ctx.response_payload.get("text", ""),
        history=ctx.history
    )
