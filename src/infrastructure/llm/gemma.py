from domain.ports import  LLMInterface
from langchain_ollama.llms import OllamaLLM
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

# Tanto llama3.2:3b y gemma3:4b funcionan correctamente. Sin embargo, llama3.2:3b es más rápido y consume menos recursos.
# gemma3:4b es más preciso y tiene un mejor rendimiento en tareas complejas.
class GEMMA(LLMInterface):
    def __init__(self):
        self.llm = OllamaLLM(
            model="gemma3:4b",  # Asegúrate que este es el nombre correcto en tu Ollama
            temperature=0.1,   # Un poco de temperatura para respuestas más naturales
            max_tokens=25
        )
        
    def generate(self, prompt: str, history: Optional[List[Tuple[str, str]]] = None) -> str:
        """
        Genera una respuesta a partir del prompt utilizando OllamaLLM,
        opcionalmente usando el historial.
        """
        logger.debug(f"LLM prompt: {prompt}")

        try:
            response = self.llm.invoke(prompt)
            logger.debug(f"LLM response: {response}")
            return response.strip() 
        except Exception as e:
            logger.error(f"Error generando texto en LLMInterface: {e}")
            return "Lo siento, tuve un problema al procesar tu solicitud con la IA."
        
