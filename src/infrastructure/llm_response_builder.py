import pathlib
from domain.entities import DialogAct
import json
from typing import List
from src.infrastructure.llm_interface import LLAMA


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
    def render(self, acts: list[DialogAct], ctx) -> str:

        template_snippets = ""
        for a in acts:
          if a.type == "ack_field":
              sample = f"Genial, seleccionamos {self._pretty(a.field)}: {a.new}. "
          elif a.type == "ask_field":
              dict = TEMPLATES.get(a.type, {}).get(a.field, {})
              sample = f"{dict.get('prompt', '')} Estas son las opciones: {', '.join(dict.get('options', []))}."
          template_snippets += f"{sample} \n"

        
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
        return response.strip()
      
      # Helper privado para nombres “bonitos”
    def _pretty(self,field: str) -> str:
        return {
            "organismo": "organismo",
            "nivel": "nivel de estudios",
            "campo_estudio": "área de estudio",
            "ubicacion": "ubicación",
        }.get(field, field)



class TemplateResponseBuilder:
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
    def render(self, acts: list[DialogAct], ctx) -> str:

        template_snippets = ""
        for a in acts:
          if a.type == "ack_field":
              sample = f"Genial, seleccionamos {self._pretty(a.field)}: {a.new}. "
          elif a.type == "modify_field":
              sample = f"Vale, cambiamos {self._pretty(a.field)} de {a.old} a {a.new}. "
          elif a.type == "ask_field":
              dict = TEMPLATES.get(a.type, {}).get(a.field, {})
              sample = f"{dict.get('prompt', '')} {self._prety_options(dict.get('options', []))}."
          template_snippets += f"{sample} \n"

        return template_snippets.strip()
      
      # Helper privado para nombres “bonitos”
    def _pretty(self,field: str) -> str:
        return {
            "organismo": "organismo",
            "nivel": "nivel de estudios",
            "campo_estudio": "área de estudio",
            "ubicacion": "ubicación",
        }.get(field, field)
        
    def _prety_options(self, options: list[str]) -> str:
        """
        Formatea una lista de opciones como un string bonito.
        Elimina los guiones bajos y pone las primeras letras en mayúscula.
        """
        def fmt(opt: str) -> str:
          return opt.replace("_", " ").capitalize()
        n = len(options)

        if n == 0:
            return ""

        if n == 1:
            return f"Solo está esta opción: {fmt(options[0])}"

        # Varias opciones → unir con comas y «y» final
        pretties = [fmt(o) for o in options]
        cuerpo = ", ".join(pretties[:-1])
        return f"Estas son las opciones: {cuerpo} y {pretties[-1]}"
