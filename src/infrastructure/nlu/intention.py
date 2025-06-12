import json
import re
from typing import Any, Optional
import logging

from domain.ports import LLMInterface, IntentExtractorService
from infrastructure.exceptions import JSONExtractionError
logger = logging.getLogger(__name__)

class IntentionExtractor(IntentExtractorService):
    def __init__(self, llm : LLMInterface):
        self.llm = llm
        self.intent_prompt = """
Analiza el contexto de conversacion y el siguiente mensaje del usuario y clasifícalo **estrictamente en UNA** de las siguientes intenciones.  
Intención anterior: {intention}
---  
1. `requisitos_beca`: el usuario pregunta por los requisitos de una beca .
   - **Ejemplos**:  
     - “¿Qué requisitios tienes la beca GVA?”  
     - “Qué tengo que cumplir para la beca Comedor”  
     - “Requisitos”  
     - “¿Quiero saber los requerimientos?”  
     - “¿Qué piden para la beca UV Destaca?”  


2. `plazos_beca`: el usuario pide información acerca de los plazos de una beca.  
   - **Ejemplos**:  
     - “¿Cuándo me podría aplicar a dicha beca?”  
     - “Quiero aplicar a la beca MEC”  
     - “Cuándo termina?”  
     - “¿Cuándo es la fecha límite?”
     - “Cuándo puedo solicitar la beca”
     

3. `buscar_por_criterio`: el usuario inicia o continúa una búsqueda guiada de becas, expresa necesidades genéricas sobre becas **o** emplea comandos de flujo para **modificar** o **omitir** criterios de búsqueda.
   - **Ejemplos de búsqueda guiada**:  
     - “necesito una beca para mi grado”  
     - “¿qué becas hay para estudiar en Francia?”  
     - “recomiéndame becas para un doctorado internacional”  
     - “para ingeniería”  


4. `general_qa`: consultas amplias o consejos sobre el proceso de solicitud, documentación o funcionamiento general, sin intención inmediata de buscar becas ni de explicación de un término específico.  
   - **Ejemplos**:  
     - “¿Qué documentos suelen pedir?”  
     - “¿Cómo es el proceso en general?”  
     
5. `otro`: cualquier otra consulta que no encaje en las categorías anteriores, como preguntas sobre el funcionamiento del sistema, errores o temas no relacionados con becas.


**Instrucciones de salida:**
Devuelve **EXCLUSIVAMENTE** un objeto JSON válido con la estructura: `{{ "intention": "..." }}`.



Contexto Previo de la conversación:
\"\"\"{context}\"\"\"

Mensaje del usuario:
\"\"\"{message}\"\"\"

JSON de salida:
"""   
    def _extract_json(self, text: str, key: str = None) -> Optional[Any]:
        """
        Extrae el primer bloque JSON bien formado del texto.
        Si key se proporciona, devuelve data[key], si no, devuelve el dict completo.
        """
        def extract_balanced_json(text: str) -> Optional[str]:
            start = text.find("{")
            if start == -1:
                return None

            open_braces = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    open_braces += 1
                elif text[i] == "}":
                    open_braces -= 1
                    if open_braces == 0:
                        return text[start:i+1]
            return None  # No cerrado correctamente

        # Prioridad a bloques delimitados con ```json ... ```
        match_block = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match_block:
            json_str = match_block.group(1)
        else:
            json_str = extract_balanced_json(text)

        if not json_str:
            logger.warning(f"No JSON found in LLM response: {text}")
            raise JSONExtractionError("Failed to decode JSON from LLM response")

        try:
            data = json.loads(json_str)
            return data.get(key) if key else data
        except json.JSONDecodeError:
            logger.error(f"JSON decoding failed: {json_str}")
            raise JSONExtractionError("Failed to decode JSON from LLM response")
          
          
    def extract(self, message: str, context: str = None, intention: str = None) -> dict:
        """
        Clasificación principal. Ahora puede tomar contexto del flujo guiado.
        """
        prompt = self.intent_prompt.format(message=message, context=context, intention=intention)
        resp = self.llm.generate(prompt)
        intent_data = self._extract_json(resp) # Obtener el dict completo
        intent = intent_data.get("intention") if isinstance(intent_data, dict) else None
        
        valid_intents = {"buscar_por_criterio", "plazos_beca", "requisitos_beca", "general_qa", "otro"}
        if intent not in valid_intents:
            logger.warning(f"Intent classification failed or returned invalid intent. Raw LLM resp: '{resp}'. Extracted: '{intent_data}'. Falling back to general_qa.")
            intent = "general_qa" 

        return {"intention": intent }