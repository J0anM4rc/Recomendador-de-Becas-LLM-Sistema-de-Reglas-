import uuid
import logging
import pathlib 
from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from application.pipeline.factory import build_pipeline
from application.pipeline.context import HandlerContext
from application.pipeline.dtos import CriteriaDTO
from application.pipeline.handlers.usecases.criteria.state_machine import CriteriaState
from infrastructure.llm.gemma import GEMMA
from infrastructure.prolog import (
    PrologConnector,
    PrologService
)
from infrastructure.nlu import (
    IntentionExtractor,
    SlotsExtractor
)



# Configuración del logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("swiplserver").setLevel(logging.WARNING)

# --- Construcción de la pipeline (composition root) --------------------
KB_PATH = pathlib.Path("config/becas.pl")

def create_pipeline():
    # 1) Adaptadores concretos
    llm = GEMMA()
    repo = PrologConnector(PrologService(kb_path=str(KB_PATH)))

    # 2) NLU
    intent_clf = IntentionExtractor(llm=llm)
    slots_clf = SlotsExtractor(llm=llm, repository=repo)

    # 3) Orquestación (capa Application)
    return build_pipeline(
        llm=llm,
        repository=repo,
        intent_clf=intent_clf,
        slots_clf=slots_clf,
    )

pipeline = create_pipeline()

# Inicialización de FastAPI y construcción de la pipeline
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELOS DE REQUEST/RESPONSE ACTUALIZADOS ---

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # Ahora el cliente solo envía esto

class ChatResponse(BaseModel):
    response: str
    session_id: str


# --- STORE EN MEMORIA DE CONTEXTOS POR session_id ---

# En un entorno real convendría usar Redis o base de datos en lugar de un dict en memoria.
contexts_store: dict[str, HandlerContext] = {}
# 1) Ruta principal que sirve el index de tu SPA
@app.get("/", response_class=FileResponse)
async def root():
    return FileResponse("static/index.html")

# 2) Monta el directorio static en /static
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    # 1. Determinar si es una nueva conversación o una existente
    if not req.session_id:
        # Primera petición: generamos un nuevo session_id y contexto vacío
        session_id = str(uuid.uuid4())
        ctx = HandlerContext(raw_text=req.message, history=[])
        ctx.intention = "buscar_por_criterio"
        ctx.arguments["criteria"] = CriteriaDTO(None, "ciencias_sociales", "publico_estatal","grado", "españa")
        ctx.criteria_sm.set_state(CriteriaState.AWAITING_CONFIRMATION)
        
    else:
        session_id = req.session_id
        # Recuperamos el contexto previo asociado al session_id
        if session_id not in contexts_store:
            raise HTTPException(status_code=400, detail="Session ID no válido")
        logging.debug(f"Session_id: {session_id}")
        logging.debug(f"Contexto previo: {contexts_store[session_id].intention}")
        logging.debug(f"Mensaje recibido: {req.message}")
        ctx = contexts_store[session_id]
        # Actualizamos solamente el mensaje crudo; mantenemos history y intention previos
        ctx.raw_text = req.message

    # 2. guardar el mensaje del usuario en el historial
    ctx.history.append({"role": "usuario", "content": req.message})
    
    # 3. Procesar pipeline con el contexto cargado
    ctx = pipeline.handle(ctx)
    
    # 4. Guardar la respuesta generada en el contexto
    assistant_msg = ctx.response_payload.get("text", "")
    ctx.history.append({"role": "asistente", "content": assistant_msg})
    
    
    # 5. Guardar el contexto actualizado en el store
    contexts_store[session_id] = ctx

    # 6. Devolver únicamente la respuesta de texto, el session_id y la última intención
    return ChatResponse(
        response=assistant_msg,
        session_id=session_id,
    )
