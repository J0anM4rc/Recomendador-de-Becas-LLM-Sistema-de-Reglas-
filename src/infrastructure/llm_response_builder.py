import pathlib
from venv import logger

import json
from pipeline.handlers.protocols import HandlerContext
from infrastructure.llm.gemma import LLAMA


SYSTEM_PROMPT = """Parafrasea **cada una** de las frases que te paso; no cambies su significado.

- Reformula frase a frase (mismo orden, mismo número de frases). 
- No añadas información nueva, no elimines nada.
- Usa un lenguaje natural, como si lo dijera una persona.
- Mantén las opciones, nombres y datos tal cual.
- Devuelve la salida **solo** como JSON válido, exactamente así:
```json
{"response_message": ["frase reformulada 1", "frase reformulada 2", ...]}
``` 

### Frases a parafrasear\n
"""

PROMPT_PATH = pathlib.Path("config/flow_config.json")
with PROMPT_PATH.open(encoding="utf-8") as fh:
    TEMPLATES = json.load(fh)


class LLMResponseBuilder:
    """
    Builder de NLG que usa LLAMA (LangChain-Ollama) en vez de OpenAI.
    """

    def __init__(
        self,
        llama_client: LLAMA | None = None,
    ):
        # Si no se inyecta nada, creamos uno con la config por defecto
        self.llm = llama_client or LLAMA()

    # ------------------------------------------------------------------
    def render(self, ctx) -> str:

        template_snippets = ""

        prompt_parts = [
            f"{SYSTEM_PROMPT}",
            f"{template_snippets}"
        ]

        if ctx.history:
             prompt_parts.append(f"Contexto: \n{ctx.last_interaction()}\n")
        #prompt_parts.append("***Salida***:\nDevuelve solo el mensaje para el usuario\nAsistente: <mensaje>")
        prompt = "\n".join(prompt_parts)
        print(f"Prompt enviado al LLM: {prompt}")
        # 4) Llamada al modelo (siempre)
        response = self.llm.generate(prompt)
        ctx.history.append({"role": "assistant", "content": response.strip()})

        return response.strip()
      
      # Helper privado para nombres “bonitos”
    def _pretty(self,field: str) -> str:
        return {
            "organismo": "organismo",
            "nivel": "nivel de estudios",
            "campo_estudio": "área de estudio",
            "ubicacion": "ubicación",
        }.get(field, field)